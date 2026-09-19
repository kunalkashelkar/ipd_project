# ============================================================
# Scan Orchestration Tasks (Phase 4 Pipeline Engine)
# ============================================================

from __future__ import annotations

import io
import shutil
import uuid
import zipfile
from pathlib import Path

from loguru import logger
from sqlalchemy import select

from backend.app.database.session import async_session_factory
from backend.app.models.ai_prediction import AIPrediction
from backend.app.models.analysis_artifact import AnalysisArtifact
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import Function, SourceFile, SourceSnapshot
from backend.app.services.ai_inference import (
    AIErrorCode,
    AIInferenceError,
    CanonicalAIRequest,
    FunctionContext,
    SourceFileContext,
    get_ai_provider,
)
from backend.app.services.finding_service import FindingCorrelationService
from backend.app.services.scan_lifecycle.lifecycle_service import ScanLifecycleService
from backend.app.services.scan_lifecycle.state_machine import ScanStage
from backend.app.services.static_analysis.process_runner import (
    ProcessCancelledError,
    ProcessTimeoutError,
)
from backend.app.services.static_analysis.service import StaticAnalysisService
from backend.app.services.static_analysis.taint_pipeline import TaintPipelineService
from backend.app.storage.service import StorageService
from backend.app.utils.zip_utils import safe_extract_zip
from backend.app.workers.base_task import AsyncCeleryTask
from backend.app.workers.celery_app import celery_app


@celery_app.task(bind=True, base=AsyncCeleryTask, name="orchestrate_scan")
async def orchestrate_scan(self, scan_id: str):
    """Master workflow orchestrator for a vulnerability scan.

    Executes:
    PREPARING -> CHECKOUT -> PREPROCESSING -> STATIC_ANALYSIS -> GRAPH_PROCESSING -> AI_ANALYSIS (RESERVED) -> POST_PROCESSING -> COMPLETED.
    """
    logger.info("Starting scan orchestration for scan {scan_id}", scan_id=scan_id)
    scan_uuid = uuid.UUID(scan_id)
    worker_id = getattr(self.request, "hostname", "celery-worker")
    workspace = Path(f"/tmp/scans/{scan_id}")

    async with async_session_factory() as db:
        lifecycle = ScanLifecycleService(db)
        storage = StorageService()
        static_service = StaticAnalysisService()
        taint_service = TaintPipelineService()

        scan = await lifecycle.get_scan(scan_uuid)

        # 1. Concurrency and terminal state check
        if scan.status in {"completed", "failed", "cancelled", "timed_out"}:
            logger.warning(
                "Scan {id} is already in terminal state '{st}'. Skipping duplicate execution.",
                id=scan_id,
                st=scan.status,
            )
            return

        try:
            # ── 1. PREPARING ───────────────────────────────────────
            await lifecycle.transition_stage(
                scan_uuid, ScanStage.PREPARING, worker_id=worker_id, metadata={"workspace": str(workspace)}
            )
            workspace.mkdir(parents=True, exist_ok=True)
            source_dir = workspace / "source"
            source_dir.mkdir(parents=True, exist_ok=True)

            if not scan.source_snapshot_id:
                raise ValueError("Scan does not reference an immutable source snapshot")

            # ── 2. CHECKOUT ────────────────────────────────────────
            await lifecycle.transition_stage(scan_uuid, ScanStage.CHECKOUT, worker_id=worker_id)

            stmt_snap = select(SourceSnapshot).where(SourceSnapshot.id == scan.source_snapshot_id)
            res_snap = await db.execute(stmt_snap)
            snapshot = res_snap.scalar_one_or_none()

            if not snapshot:
                raise ValueError(f"Referenced snapshot {scan.source_snapshot_id} was not found")
            if snapshot.status != "ready":
                raise ValueError(
                    f"Referenced snapshot {snapshot.id} is in status '{snapshot.status}'. Only READY snapshots can be scanned."
                )

            # Retrieve immutable snapshot archive from storage
            archive_bytes = await storage.read_file(snapshot.artifact_uri)
            safe_extract_zip(archive_bytes, source_dir)
            logger.info("Snapshot {snap_id} extracted to {src}", snap_id=snapshot.id, src=source_dir)

            # ── 3. PREPROCESSING ───────────────────────────────────
            await lifecycle.transition_stage(
                scan_uuid, ScanStage.PREPROCESSING, worker_id=worker_id, metadata={"snapshot_files": snapshot.file_count}
            )
            # Verify extracted files
            extracted_files = [p for p in source_dir.rglob("*") if p.is_file()]
            logger.info("Discovered {n} source files in workspace", n=len(extracted_files))

            # ── 4. STATIC ANALYSIS ─────────────────────────────────
            await lifecycle.transition_stage(scan_uuid, ScanStage.STATIC_ANALYSIS, worker_id=worker_id)
            artifacts_meta, cpg = static_service.analyze(
                source_dir=source_dir,
                workspace=workspace,
                scan_id=scan_uuid,
                snapshot_id=snapshot.id,
                config=scan.config or {},
            )

            # ── 5. GRAPH PROCESSING & TAINT ANALYSIS ───────────────
            await lifecycle.transition_stage(scan_uuid, ScanStage.GRAPH_PROCESSING, worker_id=worker_id)

            # Persist canonical graph artifacts (AST, CFG, PDG, CPG, CALL_GRAPH)
            org_id = scan.organization_id or scan.project_id
            for graph_type, meta in artifacts_meta.items():
                artifact_content = meta.artifact_path.read_bytes()
                storage_key = StorageService.scan_artifact_key(
                    org_id=org_id,
                    project_id=scan.project_id,
                    scan_id=scan_uuid,
                    artifact_type=graph_type,
                    artifact_id=meta.artifact_id,
                )
                await storage.save_object(artifact_content, storage_key)

                artifact_row = AnalysisArtifact(
                    id=meta.artifact_id,
                    scan_id=scan_uuid,
                    source_snapshot_id=snapshot.id,
                    artifact_type=graph_type,
                    schema_version=meta.schema_version,
                    artifact_uri=storage_key,
                    content_hash=meta.content_hash,
                    size_bytes=meta.size_bytes,
                    status=meta.status,
                    tool_name=meta.tool_name,
                    tool_version=meta.tool_version,
                    node_count=meta.node_count,
                    edge_count=meta.edge_count,
                    artifact_metadata=meta.metadata,
                )
                db.add(artifact_row)

            # Also execute taint analysis so canonical taint evidence is ready
            taint_meta = taint_service.run_taint_analysis(
                cpg=cpg,
                workspace=workspace,
                scan_id=scan_uuid,
                snapshot_id=snapshot.id,
            )
            taint_bytes = taint_meta.artifact_path.read_bytes()
            taint_storage_key = StorageService.scan_artifact_key(
                org_id=org_id,
                project_id=scan.project_id,
                scan_id=scan_uuid,
                artifact_type="TAINT",
                artifact_id=taint_meta.artifact_id,
            )
            await storage.save_object(taint_bytes, taint_storage_key)

            taint_row = AnalysisArtifact(
                id=taint_meta.artifact_id,
                scan_id=scan_uuid,
                source_snapshot_id=snapshot.id,
                artifact_type="TAINT",
                schema_version=taint_meta.schema_version,
                artifact_uri=taint_storage_key,
                content_hash=taint_meta.content_hash,
                size_bytes=taint_meta.size_bytes,
                status=taint_meta.status,
                tool_name=taint_meta.tool_name,
                tool_version=taint_meta.tool_version,
                node_count=taint_meta.node_count,
                edge_count=taint_meta.edge_count,
                artifact_metadata=taint_meta.metadata,
            )
            db.add(taint_row)
            await db.commit()
            logger.info("Persisted canonical graph & taint artifacts to storage & database")

            # ── 6. AI ANALYSIS (Phase 5) ───────────────────────────
            await lifecycle.transition_stage(scan_uuid, ScanStage.AI_ANALYSIS, worker_id=worker_id)

            # Query source files and functions belonging to this snapshot
            sfiles_res = await db.execute(
                select(SourceFile).where(SourceFile.source_snapshot_id == snapshot.id)
            )
            snapshot_files = list(sfiles_res.scalars().all())

            funcs_res = await db.execute(
                select(Function).join(SourceFile, Function.source_file_id == SourceFile.id).where(
                    SourceFile.source_snapshot_id == snapshot.id
                )
            )
            snapshot_funcs = list(funcs_res.scalars().all())

            # Build canonical request
            sfile_contexts = [
                SourceFileContext(
                    file_id=sf.id,
                    relative_path=sf.relative_path,
                    language=sf.language,
                    line_count=sf.line_count,
                    content_hash=sf.content_hash,
                    original_artifact_uri=sf.original_artifact_uri,
                )
                for sf in snapshot_files
            ]

            func_file_map = {sf.id: sf.relative_path for sf in snapshot_files}
            function_contexts = [
                FunctionContext(
                    function_id=fn.function_id,
                    name=fn.name,
                    relative_path=func_file_map.get(fn.source_file_id, ""),
                    start_line=fn.start_line,
                    end_line=fn.end_line,
                    signature=fn.signature,
                    token_count=fn.token_count,
                )
                for fn in snapshot_funcs
            ]

            graph_refs = {k: str(v.artifact_id) for k, v in artifacts_meta.items()}
            cpg_meta = artifacts_meta.get("CPG")

            primary_lang = None
            if snapshot.detected_languages and isinstance(snapshot.detected_languages, dict):
                primary_lang = next(iter(snapshot.detected_languages.keys()))

            ai_req = CanonicalAIRequest(
                scan_id=scan_uuid,
                source_snapshot_id=snapshot.id,
                project_id=scan.project_id,
                language=primary_lang,
                source_files=sfile_contexts,
                functions=function_contexts,
                graph_artifact_refs=graph_refs,
                cpg_ref=str(cpg_meta.artifact_id) if cpg_meta else None,
                taint_evidence_ref=str(taint_meta.artifact_id),
                feature_schema_version="v1.0.0",
                metadata={"config": scan.config or {}},
            )

            # Resolve AI Provider through factory
            ai_provider = get_ai_provider()
            logger.info(
                "Executing AI analysis using provider '{p}' (model: {m} {v})",
                p=ai_provider.provider_id,
                m=ai_provider.model_name,
                v=ai_provider.model_version,
            )

            canonical_predictions = await ai_provider.predict(ai_req)

            # Map files and functions to rows for FK integrity
            file_by_path = {sf.relative_path.replace("\\", "/").lower(): sf.id for sf in snapshot_files}
            func_by_key = {
                (fn.name.lower(), func_file_map.get(fn.source_file_id, "").replace("\\", "/").lower()): fn.id
                for fn in snapshot_funcs
            }

            persisted_predictions: list[AIPrediction] = []
            for cp in canonical_predictions:
                norm_p = cp.file_path.replace("\\", "/").lower()
                sf_id = file_by_path.get(norm_p)
                fn_id = func_by_key.get((cp.function_name.lower() if cp.function_name else "", norm_p))

                ai_row = AIPrediction(
                    id=uuid.uuid4(),
                    scan_id=scan_uuid,
                    source_snapshot_id=snapshot.id,
                    source_file_id=sf_id,
                    function_id=fn_id,
                    file_path=cp.file_path,
                    function_name=cp.function_name,
                    line_number=cp.line_number,
                    end_line=cp.end_line,
                    prediction=cp.prediction,
                    confidence=cp.confidence,
                    cwe_id=cp.cwe_id,
                    severity=cp.severity,
                    cvss_score=cp.cvss_score,
                    evidence_json=cp.evidence,
                    provider=cp.provider,
                    model_name=cp.model_name,
                    model_version=cp.model_version,
                    input_schema_version=cp.input_schema_version,
                    output_schema_version=cp.output_schema_version,
                    generated_by_ai=cp.generated_by_ai,
                )
                db.add(ai_row)
                persisted_predictions.append(ai_row)

            scan.ai_model_version = f"{ai_provider.model_name}:{ai_provider.model_version}"
            await db.commit()
            logger.info("Persisted {n} AI predictions to database", n=len(persisted_predictions))

            # ── 7. POST PROCESSING & CORRELATION (Phase 5) ─────────
            await lifecycle.transition_stage(scan_uuid, ScanStage.POST_PROCESSING, worker_id=worker_id)

            correlation_service = FindingCorrelationService(db)
            findings = await correlation_service.correlate_and_persist(
                scan=scan,
                snapshot=snapshot,
                ai_predictions=persisted_predictions,
                taint_metadata=taint_meta.metadata,
                graph_artifacts={k: str(v.artifact_id) for k, v in artifacts_meta.items()},
            )
            await db.commit()
            logger.info("Correlated {n} findings across scans", n=len(findings))

            # ── 8. COMPLETED ───────────────────────────────────────
            sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for f in findings:
                sev_counts[f.severity.lower()] = sev_counts.get(f.severity.lower(), 0) + 1

            await lifecycle.transition_stage(
                scan_uuid,
                ScanStage.COMPLETED,
                worker_id=worker_id,
                metadata={
                    "total_artifacts": len(artifacts_meta) + 1,
                    "taint_paths": taint_meta.metadata.get("path_count", 0),
                    "cpg_nodes": artifacts_meta.get("CPG", taint_meta).node_count,
                    "cpg_edges": artifacts_meta.get("CPG", taint_meta).edge_count,
                    "total_findings": len(findings),
                    "ai_predictions": len(persisted_predictions),
                    "ai_provider": ai_provider.provider_id,
                    "ai_model": ai_provider.model_name,
                    "severity_counts": sev_counts,
                },
            )
            logger.info("Scan {id} completed successfully with {n} findings!", id=scan_id, n=len(findings))

            # ── 9. DOMAIN NOTIFICATION EMISSIONS ───────────────────
            try:
                from backend.app.models.project import Project
                from backend.app.services.notification_service import NotificationService

                stmt_prj = select(Project).where(Project.id == scan.project_id)
                res_prj = await db.execute(stmt_prj)
                project = res_prj.scalar_one_or_none()
                if project:
                    notif_service = NotificationService(db)
                    await notif_service.notify_scan_completed(
                        scan_id=scan.id,
                        public_scan_id=scan.public_id,
                        project_id=project.id,
                        project_name=project.name,
                        organization_id=project.organization_id,
                    )
                    for f in findings:
                        if getattr(f, "severity", "").lower() == "critical":
                            first_seen = getattr(f, "first_seen_at", None)
                            last_seen = getattr(f, "last_seen_at", None)
                            is_new_finding = (
                                first_seen is not None
                                and last_seen is not None
                                and abs((last_seen - first_seen).total_seconds()) < 5
                            )
                            if is_new_finding:
                                await notif_service.notify_critical_finding(
                                    finding_id=f.id,
                                    finding_public_id=f.public_id,
                                    title=f.title,
                                    project_id=project.id,
                                    organization_id=project.organization_id,
                                )
                    await db.commit()
            except Exception as notif_err:
                logger.warning("Failed to emit scan completion notifications: {err}", err=notif_err)

        except ProcessCancelledError as e:
            logger.warning("Scan {id} was cancelled during execution: {err}", id=scan_id, err=e)
            await lifecycle.transition_stage(
                scan_uuid, ScanStage.CANCELLED, error_code="CANCELLED", error_message=str(e), force=True
            )
        except ProcessTimeoutError as e:
            logger.error("Scan {id} timed out: {err}", id=scan_id, err=e)
            await lifecycle.transition_stage(
                scan_uuid, ScanStage.TIMED_OUT, error_code="ANALYSIS_TIMEOUT", error_message=str(e), force=True
            )
        except Exception as e:
            logger.exception("Scan {id} failed with error: {err}", id=scan_id, err=e)
            await lifecycle.transition_stage(
                scan_uuid, ScanStage.FAILED, error_code="ANALYSIS_FAILED", error_message=str(e), force=True
            )
        finally:
            # Guaranteed cleanup of isolated per-scan temporary workspace
            try:
                if workspace.exists():
                    shutil.rmtree(workspace, ignore_errors=True)
                    logger.debug("Cleaned up temporary workspace: {ws}", ws=workspace)
            except Exception as clean_err:
                logger.warning("Failed to remove temporary workspace {ws}: {err}", ws=workspace, err=clean_err)

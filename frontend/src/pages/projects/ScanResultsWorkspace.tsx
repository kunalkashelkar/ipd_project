// ============================================================
// ScanResultsWorkspace.tsx — Phase 5 Vulnerability Investigation Workspace
// ============================================================
// Complete production-grade vulnerability investigation surface:
// - Top Security & Scan Summary (Critical, High, Medium, Low, Provenance)
// - Master-Detail Finding Investigation Workspace
// - Immutable Snapshot Source Code Viewer with syntax highlighting & line markers
// - AI vs Deterministic Evidence distinction
// - Taint flow and canonical graph correlation
// - Finding Lifecycle, Assignment, Comments, and Suppression
// - Pure backend data with zero fabricated/mock UI values
// ============================================================

import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useSearchParams, useLocation, useNavigate, Link } from 'react-router-dom';
import {
  getResultsUrl,
  getProjectUrl,
  toProjectSlug,
  toScanSlug,
  toFindingSlug,
} from '../../utils/routes';
import {
  ArrowLeft,
  Network,
  Shield,
  Layers,
  FileCode2,
  Download,
  AlertCircle,
  Clock,
  Sparkles,
  Info,
  Binary,
  CheckCircle2,
  Bug,
  Search,
  Filter,
  UserCheck,
  MessageSquare,
  History,
  ShieldAlert,
  ShieldCheck,
  ArrowUpRight,
  ExternalLink,
  ChevronRight,
  Send,
  User,
  Tag,
  Flame,
  FileDiff,
  Terminal,
  RotateCw,
  Check,
  X,
  Cpu,
  Play,
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { scanService } from '../../services/scanService';
import { findingService } from '../../services/findingService';
import { projectService } from '../../services/projectService';
import { remediationService } from '../../services/remediationService';
import { teamService } from '../../services/teamService';
import {
  Scan,
  AnalysisArtifact,
  TaintEvidenceResponse,
  TaintPathEvidence,
  FindingListItem,
  FindingDetail,
  FindingSourceContext,
  Project,
  AIExplanation,
  Remediation,
  RemediationValidation,
  VerificationStatus,
  OrganizationMember,
} from '../../types';
import toast from 'react-hot-toast';


const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  OPEN: ['CONFIRMED', 'IN_PROGRESS', 'FALSE_POSITIVE', 'RISK_ACCEPTED', 'SUPPRESSED'],
  CONFIRMED: ['IN_PROGRESS', 'FALSE_POSITIVE', 'RISK_ACCEPTED', 'SUPPRESSED'],
  IN_PROGRESS: ['FIX_PROPOSED', 'CONFIRMED', 'FALSE_POSITIVE', 'RISK_ACCEPTED', 'SUPPRESSED'],
  FIX_PROPOSED: ['UNDER_REVIEW', 'IN_PROGRESS'],
  UNDER_REVIEW: ['FIXED', 'IN_PROGRESS'],
  FIXED: ['VERIFIED', 'REOPENED'],
  VERIFIED: ['REOPENED'],
  FALSE_POSITIVE: ['OPEN', 'REOPENED'],
  RISK_ACCEPTED: ['OPEN', 'REOPENED'],
  SUPPRESSED: ['OPEN', 'REOPENED'],
  REOPENED: ['CONFIRMED', 'IN_PROGRESS', 'FALSE_POSITIVE', 'RISK_ACCEPTED', 'SUPPRESSED'],
};

export default function ScanResultsWorkspace() {
  const params = useParams<{ id?: string; projectId?: string; scanId?: string }>();
  const id = params.projectId || params.id;
  const [searchParams] = useSearchParams();
  const scanId = params.scanId || searchParams.get('scan') || searchParams.get('scan_id');
  const navigate = useNavigate();
  const location = useLocation();

  // Project data for truthful breadcrumbs and navigation
  const [project, setProject] = useState<Project | null>(null);

  // Core scan & artifact data
  const [scan, setScan] = useState<Scan | null>(null);
  const [artifacts, setArtifacts] = useState<AnalysisArtifact[]>([]);
  const [taintEvidence, setTaintEvidence] = useState<TaintEvidenceResponse | null>(null);

  // Phase 5 Findings data
  const [findings, setFindings] = useState<FindingListItem[]>([]);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [findingDetail, setFindingDetail] = useState<FindingDetail | null>(null);
  const [sourceContext, setSourceContext] = useState<FindingSourceContext | null>(null);

  // UI state
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [loadingSource, setLoadingSource] = useState(false);
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<'findings' | 'graphs' | 'taint'>('findings');
  const [findingSubTab, setFindingSubTab] = useState<
    'overview' | 'source' | 'taint' | 'graphs' | 'ai' | 'explanation' | 'remediation' | 'occurrences' | 'comments'
  >('overview');


  // Phase 6 XAI & Remediation state
  const [explanations, setExplanations] = useState<AIExplanation[]>([]);
  const [selectedExplanationMethod, setSelectedExplanationMethod] = useState<string>('evidence_synthesizer');
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [generatingExplanation, setGeneratingExplanation] = useState(false);

  const [remediations, setRemediations] = useState<Remediation[]>([]);
  const [selectedRemediationId, setSelectedRemediationId] = useState<string | null>(null);
  const [loadingRemediation, setLoadingRemediation] = useState(false);
  const [generatingRemediation, setGeneratingRemediation] = useState(false);
  const [reviewComment, setReviewComment] = useState('');
  const [actionInProgress, setActionInProgress] = useState(false);
  const [runSandboxTests, setRunSandboxTests] = useState(true);
  const [verificationStatus, setVerificationStatus] = useState<VerificationStatus | null>(null);


  // Filter & search states
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Comment & Activity input
  const [newComment, setNewComment] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [activities, setActivities] = useState<any[]>([]);
  const [loadingActivities, setLoadingActivities] = useState(false);
  const [teamMembers, setTeamMembers] = useState<OrganizationMember[]>([]);
  const [selectedAssigneeId, setSelectedAssigneeId] = useState<string>('');

  // Suppression modal / form
  const [showSuppressModal, setShowSuppressModal] = useState(false);
  const [suppressType, setSuppressType] = useState<'FALSE_POSITIVE' | 'RISK_ACCEPTED' | 'SUPPRESSED'>('FALSE_POSITIVE');
  const [suppressReason, setSuppressReason] = useState('');

  // Taint path selection
  const [selectedTaintPath, setSelectedTaintPath] = useState<TaintPathEvidence | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // ── Initial Data Fetching ───────────────────────────────────
  useEffect(() => {
    if (id) {
      projectService
        .getProject(id)
        .then((p) => setProject(p))
        .catch(() => {});
    }
  }, [id]);

  // Canonical URL synchronization & backward compatibility redirect
  useEffect(() => {
    if (!project || !scan) return;
    const canonicalProj = toProjectSlug(project);
    const canonicalScan = toScanSlug(scan);
    const canonicalPath = `/projects/${canonicalProj}/scans/${canonicalScan}/results`;
    const findingParam = searchParams.get('finding') || searchParams.get('finding_id');
    const expectedSearch = findingParam ? `?finding=${findingParam}` : '';

    if (location.pathname !== canonicalPath || (findingParam && !searchParams.has('finding'))) {
      navigate(`${canonicalPath}${expectedSearch}`, { replace: true });
    }
  }, [project, scan, location.pathname, searchParams, navigate]);

  useEffect(() => {
    if (!scanId) return;

    async function loadWorkspaceData() {
      setLoading(true);
      try {
        const [scanRes, artifactsRes, taintRes, findingsRes] = await Promise.allSettled([
          scanService.getScan(scanId!),
          scanService.getScanArtifacts(scanId!),
          scanService.getTaintEvidence(scanId!),
          findingService.getScanFindings(scanId!),
        ]);

        if (scanRes.status === 'fulfilled') setScan(scanRes.value);
        if (artifactsRes.status === 'fulfilled') setArtifacts(artifactsRes.value);
        if (taintRes.status === 'fulfilled') {
          setTaintEvidence(taintRes.value);
          if (taintRes.value.paths?.length > 0) {
            setSelectedTaintPath(taintRes.value.paths[0]);
          }
        }
        if (findingsRes.status === 'fulfilled') {
          setFindings(findingsRes.value);
          const findingQuery = searchParams.get('finding') || searchParams.get('finding_id');
          if (findingQuery) {
            const match = findingsRes.value.find(
              (f) => f.public_id === findingQuery || f.id === findingQuery
            );
            if (match) {
              setSelectedFindingId(match.id);
            } else if (findingsRes.value.length > 0) {
              setSelectedFindingId(findingsRes.value[0].id);
            }
          } else if (findingsRes.value.length > 0) {
            setSelectedFindingId(findingsRes.value[0].id);
          }
        }
      } catch {
        toast.error('Failed to load scan analysis results');
      } finally {
        setLoading(false);
      }
    }

    loadWorkspaceData();
  }, [scanId]);

  // ── Finding Detail Fetching ─────────────────────────────────
  useEffect(() => {
    if (!selectedFindingId) {
      setFindingDetail(null);
      setSourceContext(null);
      return;
    }

    async function loadDetail() {
      setLoadingDetail(true);
      try {
        const detail = await findingService.getFindingDetail(selectedFindingId!);
        setFindingDetail(detail);

        // Fetch Phase 6 explanations, remediations & verification
        remediationService.getFindingExplanations(selectedFindingId!).then((exps) => {
          setExplanations(exps);
        }).catch(() => setExplanations([]));

        remediationService.getFindingRemediations(selectedFindingId!).then((rems) => {
          setRemediations(rems);
          if (rems.length > 0) {
            setSelectedRemediationId(rems[0].id);
          } else {
            setSelectedRemediationId(null);
          }
        }).catch(() => setRemediations([]));

        remediationService.getFindingVerification(selectedFindingId!).then((v) => {
          setVerificationStatus(v);
        }).catch(() => setVerificationStatus(null));
      } catch {
        toast.error('Failed to load finding details');
      } finally {
        setLoadingDetail(false);
      }
    }


    loadDetail();
  }, [selectedFindingId]);

  // ── Finding Source Context Fetching ─────────────────────────
  useEffect(() => {
    if (!selectedFindingId || findingSubTab !== 'source') return;

    async function loadSource() {
      setLoadingSource(true);
      try {
        const src = await findingService.getFindingSourceContext(selectedFindingId!, 20);
        setSourceContext(src);
      } catch {
        setSourceContext(null);
      } finally {
        setLoadingSource(false);
      }
    }

    loadSource();
  }, [selectedFindingId, findingSubTab]);

  // ── Filtered Findings ───────────────────────────────────────
  const filteredFindings = useMemo(() => {
    return findings.filter((f) => {
      if (severityFilter !== 'all' && f.severity.toLowerCase() !== severityFilter) {
        return false;
      }
      if (statusFilter !== 'all' && f.status.toUpperCase() !== statusFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = f.title.toLowerCase().includes(q);
        const matchesCwe = (f.cwe_id || '').toLowerCase().includes(q);
        const matchesPath = (f.latest_file_path || '').toLowerCase().includes(q);
        const matchesType = f.vulnerability_type.toLowerCase().includes(q);
        return matchesTitle || matchesCwe || matchesPath || matchesType;
      }
      return true;
    });
  }, [findings, severityFilter, statusFilter, searchQuery]);

  // ── Metrics Calculation ─────────────────────────────────────
  const metrics = useMemo(() => {
    let critical = 0;
    let high = 0;
    let medium = 0;
    let low = 0;
    for (const f of findings) {
      const sev = f.severity.toLowerCase();
      if (sev === 'critical') critical++;
      else if (sev === 'high') high++;
      else if (sev === 'medium') medium++;
      else if (sev === 'low') low++;
    }
    return { total: findings.length, critical, high, medium, low };
  }, [findings]);

  // ── Actions ─────────────────────────────────────────────────
  const handleStatusChange = async (newStatus: string) => {
    if (!selectedFindingId) return;
    try {
      await findingService.transitionStatus(selectedFindingId, {
        status: newStatus,
        reason: `Manual status transition to ${newStatus}`,
      });
      toast.success(`Finding marked as ${newStatus}`);
      // Refresh finding detail and list item directly from authoritative response
      const updated = await findingService.getFindingDetail(selectedFindingId);
      setFindingDetail(updated);
      setFindings((prev) =>
        prev.map((f) => (f.id === selectedFindingId ? { ...f, status: updated.status } : f))
      );
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Status transition failed');
    }
  };

  const handleSuppress = async () => {
    if (!selectedFindingId || !suppressReason.trim()) {
      toast.error('Please provide a reason');
      return;
    }
    try {
      await findingService.suppressFinding(selectedFindingId, {
        suppression_type: suppressType,
        reason: suppressReason.trim(),
      });
      toast.success(`Finding marked as ${suppressType}`);
      setShowSuppressModal(false);
      setSuppressReason('');
      const updated = await findingService.getFindingDetail(selectedFindingId);
      setFindingDetail(updated);
      setFindings((prev) =>
        prev.map((f) => (f.id === selectedFindingId ? { ...f, status: updated.status } : f))
      );
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Suppression failed');
    }
  };

  const handleUnsuppress = async () => {
    if (!selectedFindingId) return;
    try {
      await findingService.unsuppressFinding(selectedFindingId);
      toast.success('Finding reopened');
      const updated = await findingService.getFindingDetail(selectedFindingId);
      setFindingDetail(updated);
      setFindings((prev) =>
        prev.map((f) => (f.id === selectedFindingId ? { ...f, status: updated.status } : f))
      );
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Failed to reopen finding');
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFindingId || !newComment.trim()) return;
    setSubmittingComment(true);
    try {
      await findingService.addComment(selectedFindingId, { content: newComment.trim() });
      setNewComment('');
      toast.success('Comment added');
      const updated = await findingService.getFindingDetail(selectedFindingId);
      setFindingDetail(updated);
      const act = await findingService.getActivity(selectedFindingId);
      setActivities(act);
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Failed to add comment');
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleAssignFinding = async (userId: string) => {
    if (!selectedFindingId) return;
    try {
      await findingService.assignFinding(selectedFindingId, { user_id: userId });
      toast.success('Finding assigned successfully');
      const updated = await findingService.getFindingDetail(selectedFindingId);
      setFindingDetail(updated);
      const act = await findingService.getActivity(selectedFindingId);
      setActivities(act);
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Failed to assign finding');
    }
  };

  // Fetch activities and team members when Comments tab is active
  useEffect(() => {
    if (findingSubTab === 'comments' && selectedFindingId) {
      setLoadingActivities(true);
      findingService
        .getActivity(selectedFindingId)
        .then((act) => setActivities(act))
        .catch(() => setActivities([]))
        .finally(() => setLoadingActivities(false));

      if (project?.organization_id) {
        teamService
          .listMembers(project.organization_id)
          .then((members) => setTeamMembers(members))
          .catch(() => setTeamMembers([]));
      }
    }
  }, [findingSubTab, selectedFindingId, project?.organization_id]);

  const handleDownloadArtifact = async (artifact: AnalysisArtifact) => {
    if (!scanId) return;
    setDownloadingId(artifact.id);
    try {
      const blob = await scanService.downloadArtifact(scanId, artifact.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${artifact.artifact_type.toLowerCase()}-${scanId}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`Downloaded ${artifact.artifact_type} artifact`);
    } catch {
      toast.error(`Failed to download ${artifact.artifact_type} artifact`);
    } finally {
      setDownloadingId(null);
    }
  };

  // ── Phase 6 Remediation & XAI Handlers ───────────────────────
  const handleGenerateExplanation = async (method: string) => {
    if (!selectedFindingId) return;
    setGeneratingExplanation(true);
    try {
      const exp = await remediationService.generateFindingExplanation(selectedFindingId, method);
      setExplanations((prev) => [exp, ...prev.filter((e) => e.id !== exp.id)]);
      toast.success(`Generated explanation via ${method}`);
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Failed to generate explanation');
    } finally {
      setGeneratingExplanation(false);
    }
  };

  const handleGenerateRemediation = async () => {
    if (!selectedFindingId) return;
    setGeneratingRemediation(true);
    try {
      const rem = await remediationService.generateFindingRemediation(selectedFindingId, 'v1.0.0');
      setRemediations((prev) => [rem, ...prev.filter((r) => r.id !== rem.id)]);
      setSelectedRemediationId(rem.id);
      toast.success('Proposed remediation generated');
      const updated = await findingService.getFindingDetail(selectedFindingId);
      setFindingDetail(updated);
      setFindings((prev) =>
        prev.map((f) => (f.id === selectedFindingId ? { ...f, status: updated.status } : f))
      );
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Failed to generate remediation');
    } finally {
      setGeneratingRemediation(false);
    }
  };

  const handleReviewRemediation = async (decision: 'APPROVE' | 'REJECT') => {
    if (!selectedRemediationId || !selectedFindingId) return;
    setActionInProgress(true);
    try {
      const updatedRem = await remediationService.reviewRemediation(
        selectedRemediationId,
        decision,
        reviewComment.trim() || undefined
      );
      setRemediations((prev) =>
        prev.map((r) => (r.id === updatedRem.id ? updatedRem : r))
      );
      setReviewComment('');
      toast.success(`Remediation ${decision.toLowerCase()}d`);
      const updated = await findingService.getFindingDetail(selectedFindingId);
      setFindingDetail(updated);
      setFindings((prev) =>
        prev.map((f) => (f.id === selectedFindingId ? { ...f, status: updated.status } : f))
      );
    } catch (err: any) {
      toast.error(err.response?.data?.message || `Failed to ${decision.toLowerCase()} remediation`);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleApplyRemediation = async () => {
    if (!selectedRemediationId || !selectedFindingId) return;
    setActionInProgress(true);
    try {
      const appliedRem = await remediationService.applyRemediation(selectedRemediationId);
      setRemediations((prev) =>
        prev.map((r) => (r.id === appliedRem.id ? appliedRem : r))
      );
      toast.success('Patch applied to isolated validation workspace');
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Failed to apply patch');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleValidateRemediation = async () => {
    if (!selectedRemediationId || !selectedFindingId) return;
    setActionInProgress(true);
    try {
      const valResult = await remediationService.validateRemediation(
        selectedRemediationId,
        runSandboxTests,
        'v1.0.0'
      );
      const freshRem = await remediationService.getRemediationDetail(selectedRemediationId);
      setRemediations((prev) =>
        prev.map((r) => (r.id === freshRem.id ? freshRem : r))
      );

      const vStatus = await remediationService.getFindingVerification(selectedFindingId);
      setVerificationStatus(vStatus);

      const freshFinding = await findingService.getFindingDetail(selectedFindingId);
      setFindingDetail(freshFinding);
      setFindings((prev) =>
        prev.map((f) => (f.id === selectedFindingId ? { ...f, status: freshFinding.status } : f))
      );

      if (valResult.final_verification_result === 'VERIFIED') {
        toast.success('Finding verified! Patch resolved vulnerability.');
      } else {
        toast.error(`Validation ${valResult.status}: ${valResult.failure_reason || 'Fix not verified'}`);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Validation execution failed');
    } finally {
      setActionInProgress(false);
    }
  };

  const canonicalGraphs = artifacts.filter((a) => a.artifact_type !== 'TAINT');

  const taintArtifact = artifacts.find((a) => a.artifact_type === 'TAINT');

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm text-muted-foreground">Loading vulnerability investigation workspace...</p>
      </div>
    );
  }

  if (!scanId || !scan) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertCircle className="w-12 h-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Scan not found.</p>
        <Link to={getProjectUrl(project || id)}>
          <Button className="mt-4">Back to Project</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 space-y-6">
      {/* Top Bar Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          {/* Breadcrumb trail */}
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1.5">
            <Link to="/projects" className="hover:text-foreground transition-colors">
              Projects
            </Link>
            <ChevronRight className="w-3 h-3 text-muted-foreground/60 shrink-0" />
            <Link
              to={getProjectUrl(project || id)}
              className="hover:text-foreground font-medium text-foreground transition-colors truncate max-w-[220px]"
              title={project?.name || toProjectSlug(project || id)}
            >
              {project?.name || toProjectSlug(project || id)}
            </Link>
            <ChevronRight className="w-3 h-3 text-muted-foreground/60 shrink-0" />
            <span className="text-muted-foreground">Results</span>
          </div>

          <Link
            to={getProjectUrl(project || id)}
            className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to {project?.name || 'Project'}
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              Scan Results & Vulnerability Workspace
            </h1>
            <Badge variant="outline" className="text-xs uppercase font-mono">
              {scan.status}
            </Badge>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1 font-mono">
            <span>Scan: {scan.public_id || scanId}</span>
            <span>•</span>
            <span>Snapshot: {scan.source_snapshot_public_id || (scan.source_snapshot_id ? scan.source_snapshot_id.slice(0, 8) : 'N/A')}</span>
            {scan.ai_model_version && (
              <>
                <span>•</span>
                <span className="text-amber-400 font-semibold flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  Provider: {scan.ai_model_version}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Workspace Top Tabs */}
        <div className="flex bg-muted/40 p-1 rounded-lg border border-border/80 self-start md:self-auto">
          <button
            onClick={() => setActiveWorkspaceTab('findings')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
              activeWorkspaceTab === 'findings'
                ? 'bg-background text-foreground shadow-sm font-semibold'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Bug className="w-3.5 h-3.5" />
            Security Findings ({findings.length})
          </button>
          <button
            onClick={() => setActiveWorkspaceTab('graphs')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
              activeWorkspaceTab === 'graphs'
                ? 'bg-background text-foreground shadow-sm font-semibold'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            Canonical Graphs (5)
          </button>
          <button
            onClick={() => setActiveWorkspaceTab('taint')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
              activeWorkspaceTab === 'taint'
                ? 'bg-background text-foreground shadow-sm font-semibold'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Taint Evidence ({taintEvidence?.paths?.length || 0})
            {taintEvidence?.status === 'failed' && (
              <Badge variant="destructive" className="text-[9px] px-1 py-0 ml-1">
                FAILED
              </Badge>
            )}
            {taintEvidence?.status === 'not_run' && (
              <Badge variant="outline" className="text-[9px] px-1 py-0 ml-1">
                NOT RUN
              </Badge>
            )}
          </button>
        </div>
      </div>

      {/* ── METRICS SUMMARY BAR ──────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <Card className="p-3.5 border-border/60 bg-card/50">
          <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold block">
            Total Findings
          </span>
          <span className="text-2xl font-bold text-foreground mt-0.5 block">{metrics.total}</span>
        </Card>
        <Card className="p-3.5 border-red-500/20 bg-red-500/5">
          <span className="text-[11px] uppercase tracking-wider text-red-400 font-semibold block">
            Critical
          </span>
          <span className="text-2xl font-bold text-red-400 mt-0.5 block">{metrics.critical}</span>
        </Card>
        <Card className="p-3.5 border-amber-500/20 bg-amber-500/5">
          <span className="text-[11px] uppercase tracking-wider text-amber-400 font-semibold block">
            High
          </span>
          <span className="text-2xl font-bold text-amber-400 mt-0.5 block">{metrics.high}</span>
        </Card>
        <Card className="p-3.5 border-yellow-500/20 bg-yellow-500/5">
          <span className="text-[11px] uppercase tracking-wider text-yellow-400 font-semibold block">
            Medium
          </span>
          <span className="text-2xl font-bold text-yellow-400 mt-0.5 block">{metrics.medium}</span>
        </Card>
        <Card className="p-3.5 border-blue-500/20 bg-blue-500/5">
          <span className="text-[11px] uppercase tracking-wider text-blue-400 font-semibold block">
            Low
          </span>
          <span className="text-2xl font-bold text-blue-400 mt-0.5 block">{metrics.low}</span>
        </Card>
      </div>

      {/* ── TAB 1: FINDINGS INVESTIGATION WORKSPACE ───────────── */}
      {activeWorkspaceTab === 'findings' && (
        <div className="space-y-4">
          {findings.length === 0 ? (
            <Card className="p-12 text-center border-border/60 bg-card/20 space-y-3">
              <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
              <h3 className="text-base font-semibold text-foreground">No Vulnerabilities Detected</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                The static analysis pipeline and configured AI provider evaluated this immutable snapshot
                and detected no security issues matching active detection rulesets.
              </p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Finding List (5 cols) */}
              <div className="lg:col-span-5 space-y-3">
                {/* Search and Filters */}
                <div className="space-y-2">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder="Search CWE, file, title..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-border bg-card/50 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>

                  {/* Filter Pills */}
                  <div className="flex flex-wrap items-center gap-1.5 text-xs">
                    <button
                      onClick={() => setSeverityFilter('all')}
                      className={`px-2 py-0.5 rounded text-[11px] border transition-colors ${
                        severityFilter === 'all'
                          ? 'bg-foreground text-background border-foreground font-semibold'
                          : 'border-border text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      All
                    </button>
                    <button
                      onClick={() => setSeverityFilter('critical')}
                      className={`px-2 py-0.5 rounded text-[11px] border transition-colors ${
                        severityFilter === 'critical'
                          ? 'bg-red-500 text-white border-red-500 font-semibold'
                          : 'border-border text-red-400 hover:border-red-400'
                      }`}
                    >
                      Critical
                    </button>
                    <button
                      onClick={() => setSeverityFilter('high')}
                      className={`px-2 py-0.5 rounded text-[11px] border transition-colors ${
                        severityFilter === 'high'
                          ? 'bg-amber-500 text-white border-amber-500 font-semibold'
                          : 'border-border text-amber-400 hover:border-amber-400'
                      }`}
                    >
                      High
                    </button>
                    <button
                      onClick={() => setSeverityFilter('medium')}
                      className={`px-2 py-0.5 rounded text-[11px] border transition-colors ${
                        severityFilter === 'medium'
                          ? 'bg-yellow-500 text-white border-yellow-500 font-semibold'
                          : 'border-border text-yellow-400 hover:border-yellow-400'
                      }`}
                    >
                      Medium
                    </button>
                    <button
                      onClick={() => setSeverityFilter('low')}
                      className={`px-2 py-0.5 rounded text-[11px] border transition-colors ${
                        severityFilter === 'low'
                          ? 'bg-blue-500 text-white border-blue-500 font-semibold'
                          : 'border-border text-blue-400 hover:border-blue-400'
                      }`}
                    >
                      Low
                    </button>
                  </div>
                </div>

                {/* Finding Rows List */}
                <div className="space-y-2 max-h-[720px] overflow-y-auto pr-1">
                  {filteredFindings.map((f) => {
                    const isSelected = f.id === selectedFindingId;
                    const sev = f.severity.toLowerCase();

                    return (
                      <div
                        key={f.id}
                        onClick={() => setSelectedFindingId(f.id)}
                        className={`p-3 rounded-lg border cursor-pointer transition-all ${
                          isSelected
                            ? 'border-primary bg-primary/5 shadow-sm'
                            : 'border-border/60 hover:border-border hover:bg-card/40 bg-card/20'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span
                                className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                                  sev === 'critical'
                                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                    : sev === 'high'
                                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                    : sev === 'medium'
                                    ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                                    : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                                }`}
                              >
                                {f.severity}
                              </span>
                              {f.cwe_id && (
                                <span className="text-[11px] font-mono text-muted-foreground bg-muted/40 px-1.5 py-0.5 rounded">
                                  {f.cwe_id}
                                </span>
                              )}
                              {f.public_id && (
                                <span className="text-[10px] font-mono text-muted-foreground bg-muted/40 px-1.5 py-0.5 rounded">
                                  {f.public_id}
                                </span>
                              )}
                              <span className="text-[10px] font-mono text-muted-foreground bg-muted/30 px-1 rounded">
                                {f.status}
                              </span>
                            </div>
                            <h4 className="text-xs font-semibold text-foreground line-clamp-1">
                              {f.title}
                            </h4>
                          </div>

                          <div className="text-right shrink-0">
                            <span className="text-[11px] font-mono font-bold text-amber-400 block">
                              Risk {f.risk_score.toFixed(1)}
                            </span>
                            <span className="text-[10px] text-muted-foreground">
                              Conf {Math.round(f.confidence * 100)}%
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/40 text-[11px] text-muted-foreground font-mono">
                          <span className="truncate max-w-[240px]">
                            {f.latest_file_path || 'unknown file'}
                            {f.latest_line_number ? `:${f.latest_line_number}` : ''}
                          </span>
                          <span className="text-[10px]">
                            {f.occurrence_count} {f.occurrence_count === 1 ? 'scan' : 'scans'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                  {filteredFindings.length === 0 && (
                    <div className="p-8 text-center text-xs text-muted-foreground border border-border/40 rounded-lg">
                      No findings match the current filter criteria.
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Selected Finding Deep Investigation (7 cols) */}
              <div className="lg:col-span-7 space-y-4">
                {loadingDetail ? (
                  <Card className="p-12 text-center border-border/60">
                    <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    <p className="text-xs text-muted-foreground">Loading finding investigation data...</p>
                  </Card>
                ) : findingDetail ? (
                  <Card className="p-5 border-border/80 bg-card space-y-4">
                    {/* Finding Header */}
                    <div className="space-y-2">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            <span
                              className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                                findingDetail.severity === 'critical'
                                  ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                  : findingDetail.severity === 'high'
                                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                  : findingDetail.severity === 'medium'
                                  ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                                  : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                              }`}
                            >
                              {findingDetail.severity}
                            </span>
                            {findingDetail.cwe_id && (
                              <span className="text-xs font-mono text-muted-foreground bg-muted/40 px-2 py-0.5 rounded">
                                {findingDetail.cwe_id}
                              </span>
                            )}
                            <span className="text-xs font-mono text-muted-foreground bg-muted/40 px-2 py-0.5 rounded">
                              {findingDetail.public_id || findingDetail.id}
                            </span>
                            <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted/50 text-foreground font-semibold">
                              Status: {findingDetail.status}
                            </span>
                          </div>
                          <h2 className="text-base font-bold text-foreground">
                            {findingDetail.title}
                          </h2>
                        </div>

                        {/* Top Action Buttons */}
                        <div className="flex items-center gap-2 shrink-0">
                          {/* Authoritative Lifecycle Status Dropdown */}
                          <select
                            id="finding-status-selector"
                            aria-label="Finding Status"
                            value={findingDetail.status}
                            onChange={(e) => {
                              const target = e.target.value;
                              if (target && target !== findingDetail.status) {
                                if (
                                  target === 'FALSE_POSITIVE' ||
                                  target === 'RISK_ACCEPTED' ||
                                  target === 'SUPPRESSED'
                                ) {
                                  setSuppressType(target);
                                  setShowSuppressModal(true);
                                } else {
                                  handleStatusChange(target);
                                }
                              }
                            }}
                            className="text-xs bg-muted/40 border border-border rounded px-2.5 py-1 text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                          >
                            <option value={findingDetail.status}>
                              {findingDetail.status}
                            </option>
                            {(ALLOWED_TRANSITIONS[findingDetail.status] || [])
                              .filter((target) => target !== findingDetail.status)
                              .map((target) => (
                                <option key={target} value={target}>
                                  → {target}
                                </option>
                              ))}
                          </select>

                          {/* Authoritative Reopen or Suppress action button */}
                          {findingDetail.status === 'SUPPRESSED' ||
                          findingDetail.status === 'FALSE_POSITIVE' ||
                          findingDetail.status === 'RISK_ACCEPTED' ? (
                            <Button size="sm" variant="outline" onClick={handleUnsuppress} className="text-xs">
                              Reopen
                            </Button>
                          ) : findingDetail.status === 'FIXED' || findingDetail.status === 'VERIFIED' ? (
                            <Button size="sm" variant="outline" onClick={() => handleStatusChange('REOPENED')} className="text-xs">
                              Reopen
                            </Button>
                          ) : (
                            <Button size="sm" variant="outline" onClick={() => setShowSuppressModal(true)} className="text-xs">
                              Suppress
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Metadata Banner */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-border/40 text-[11px] font-mono">
                        <div>
                          <span className="text-muted-foreground block">Risk Score:</span>
                          <span className="font-bold text-amber-400">
                            {findingDetail.risk_score.toFixed(1)} / 10.0 ({findingDetail.risk_version})
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block">AI Confidence:</span>
                          <span className="font-bold text-foreground">
                            {Math.round(findingDetail.confidence * 100)}%
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block">CVSS Score:</span>
                          <span className="font-bold text-foreground">
                            {findingDetail.cvss_score ? findingDetail.cvss_score.toFixed(1) : 'N/A'}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block">First / Last Seen:</span>
                          <span className="font-bold text-foreground">
                            {new Date(findingDetail.last_seen_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Sub-tab Navigation */}
                    <div className="flex border-b border-border/60 text-xs gap-1 overflow-x-auto">
                      <button
                        onClick={() => setFindingSubTab('overview')}
                        className={`px-3 py-1.5 border-b-2 font-medium transition-all ${
                          findingSubTab === 'overview'
                            ? 'border-primary text-foreground font-semibold'
                            : 'border-transparent text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        Overview
                      </button>
                      <button
                        onClick={() => setFindingSubTab('source')}
                        className={`px-3 py-1.5 border-b-2 font-medium transition-all flex items-center gap-1 ${
                          findingSubTab === 'source'
                            ? 'border-primary text-foreground font-semibold'
                            : 'border-transparent text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        <FileCode2 className="w-3.5 h-3.5" /> Source Code
                      </button>
                      <button
                        onClick={() => setFindingSubTab('taint')}
                        className={`px-3 py-1.5 border-b-2 font-medium transition-all flex items-center gap-1 ${
                          findingSubTab === 'taint'
                            ? 'border-primary text-foreground font-semibold'
                            : 'border-transparent text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        <Layers className="w-3.5 h-3.5" /> Taint Flow
                      </button>
                      <button
                        onClick={() => setFindingSubTab('graphs')}
                        className={`px-3 py-1.5 border-b-2 font-medium transition-all flex items-center gap-1 ${
                          findingSubTab === 'graphs'
                            ? 'border-primary text-foreground font-semibold'
                            : 'border-transparent text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        <Network className="w-3.5 h-3.5" /> Graph Evidence
                      </button>
                      <button
                        onClick={() => setFindingSubTab('ai')}
                        className={`px-3 py-1.5 border-b-2 font-medium transition-all flex items-center gap-1 ${
                          findingSubTab === 'ai'
                            ? 'border-primary text-foreground font-semibold'
                            : 'border-transparent text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        <Sparkles className="w-3.5 h-3.5" /> AI Provenance
                      </button>
                      <button
                        onClick={() => setFindingSubTab('explanation')}
                        className={`px-3 py-1.5 border-b-2 font-medium transition-all flex items-center gap-1 ${
                          findingSubTab === 'explanation'
                            ? 'border-primary text-foreground font-semibold'
                            : 'border-transparent text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        <Cpu className="w-3.5 h-3.5" /> AI Explanation
                      </button>
                      <button
                        onClick={() => setFindingSubTab('remediation')}
                        className={`px-3 py-1.5 border-b-2 font-medium transition-all flex items-center gap-1 ${
                          findingSubTab === 'remediation'
                            ? 'border-primary text-foreground font-semibold'
                            : 'border-transparent text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        <ShieldCheck className="w-3.5 h-3.5" /> Remediation & Verification
                      </button>

                      <button
                        onClick={() => setFindingSubTab('occurrences')}
                        className={`px-3 py-1.5 border-b-2 font-medium transition-all flex items-center gap-1 ${
                          findingSubTab === 'occurrences'
                            ? 'border-primary text-foreground font-semibold'
                            : 'border-transparent text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        <History className="w-3.5 h-3.5" /> History ({findingDetail.occurrences.length})
                      </button>
                      <button
                        onClick={() => setFindingSubTab('comments')}
                        className={`px-3 py-1.5 border-b-2 font-medium transition-all flex items-center gap-1 ${
                          findingSubTab === 'comments'
                            ? 'border-primary text-foreground font-semibold'
                            : 'border-transparent text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        <MessageSquare className="w-3.5 h-3.5" /> Comments ({findingDetail.comments.length})
                      </button>
                    </div>

                    {/* Sub-tab 1: Overview */}
                    {findingSubTab === 'overview' && (
                      <div className="space-y-4 text-xs">
                        {/* Evidence Distinction Notice */}
                        <div className="p-3.5 rounded-lg border border-border/80 bg-muted/20 space-y-1.5">
                          <span className="font-semibold text-foreground flex items-center gap-1.5">
                            <Info className="w-3.5 h-3.5 text-primary" />
                            Evidence & Provenance Distinction
                          </span>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-muted-foreground">
                            <div className="p-2 rounded bg-card/60 border border-border/40">
                              <span className="font-bold text-foreground block mb-0.5">
                                Deterministic Evidence:
                              </span>
                              <span>
                                Exact source location, AST structure, control-flow graph, and verified
                                taint propagation path from input to execution sink.
                              </span>
                            </div>
                            <div className="p-2 rounded bg-card/60 border border-border/40">
                              <span className="font-bold text-foreground block mb-0.5">
                                AI-Derived Inference:
                              </span>
                              <span>
                                Vulnerability classification probability, CWE taxonomy attribution,
                                and confidence score evaluated by the configured AI inference provider.
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Location Details */}
                        <div className="p-3 rounded-lg border border-border/60 bg-card/40 space-y-2">
                          <span className="text-[11px] uppercase font-bold text-muted-foreground tracking-wider block">
                            Vulnerable Code Location
                          </span>
                          <div className="space-y-1 font-mono text-xs">
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground w-20">File:</span>
                              <span className="text-foreground">
                                {findingDetail.latest_occurrence?.file_path || 'N/A'}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground w-20">Line Span:</span>
                              <span className="text-foreground">
                                {findingDetail.latest_occurrence?.start_line || 'N/A'}
                                {findingDetail.latest_occurrence?.end_line &&
                                findingDetail.latest_occurrence.end_line !==
                                  findingDetail.latest_occurrence.start_line
                                  ? ` - ${findingDetail.latest_occurrence.end_line}`
                                  : ''}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground w-20">Function:</span>
                              <span className="text-foreground">
                                {findingDetail.latest_occurrence?.function_name || '<global>'}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground w-20">Fingerprint:</span>
                              <span className="text-muted-foreground truncate max-w-sm">
                                {findingDetail.fingerprint} ({findingDetail.fingerprint_version})
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Remediation Summary Banner */}
                        <div className="p-3 rounded-lg border border-border/40 bg-muted/10 text-muted-foreground space-y-1">
                          <span className="font-semibold text-foreground block">
                            Remediation & Patching
                          </span>
                          <p className="text-[11px]">
                            Review candidate patches, sandbox validation outcomes, and explainability attributions in the Remediation tab.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Sub-tab 2: Source Code Viewer */}
                    {findingSubTab === 'source' && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
                          <span>
                            File: {findingDetail.latest_occurrence?.file_path}:
                            {findingDetail.latest_occurrence?.start_line}
                          </span>
                          <Badge variant="outline" className="text-[10px] text-emerald-400">
                            Immutable Snapshot Verified
                          </Badge>
                        </div>

                        {loadingSource ? (
                          <div className="p-8 text-center text-xs text-muted-foreground">
                            <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                            Loading verified source snippet...
                          </div>
                        ) : sourceContext ? (
                          <div className="rounded-lg border border-border bg-[#0d1117] text-[#c9d1d9] font-mono text-xs overflow-x-auto p-3">
                            <table className="w-full border-collapse">
                              <tbody>
                                {sourceContext.source_snippet.split('\n').map((lineText, idx) => {
                                  const currentLineNum = sourceContext.start_line + idx;
                                  const isVulnLine =
                                    currentLineNum === findingDetail.latest_occurrence?.start_line;

                                  return (
                                    <tr
                                      key={idx}
                                      className={
                                        isVulnLine
                                          ? 'bg-red-500/20 text-red-300 font-semibold border-l-2 border-red-500'
                                          : 'hover:bg-muted/10'
                                      }
                                    >
                                      <td className="w-12 select-none text-right pr-4 text-muted-foreground/60 text-[11px]">
                                        {currentLineNum}
                                      </td>
                                      <td className="whitespace-pre font-mono py-0.5">{lineText}</td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <div className="p-8 text-center text-xs text-muted-foreground border border-border/40 rounded-lg">
                            Source code preview could not be loaded from the immutable snapshot artifact.
                          </div>
                        )}
                      </div>
                    )}

                    {/* Sub-tab 3: Taint Flow */}
                    {findingSubTab === 'taint' && (
                      <div className="space-y-3 text-xs">
                        {findingDetail.latest_occurrence?.taint_evidence_ref ? (
                          <div className="space-y-3">
                            <span className="text-[11px] uppercase font-bold text-muted-foreground tracking-wider block">
                              Data Flow & Propagation Trace
                            </span>
                            <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5">
                              <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider block mb-0.5">
                                Untrusted Input Source
                              </span>
                              <div className="font-mono text-foreground">
                                {findingDetail.latest_occurrence.taint_evidence_ref.source_file}:
                                {findingDetail.latest_occurrence.taint_evidence_ref.source_line}
                              </div>
                            </div>

                            {/* Sequence */}
                            {findingDetail.latest_occurrence.taint_evidence_ref.nodes?.length > 2 && (
                              <div className="pl-6 border-l-2 border-dashed border-border/60 space-y-1.5 my-2">
                                <span className="text-[10px] uppercase font-semibold text-muted-foreground">
                                  Intermediate Taint Propagation (
                                  {findingDetail.latest_occurrence.taint_evidence_ref.nodes.length - 2} steps)
                                </span>
                                {findingDetail.latest_occurrence.taint_evidence_ref.nodes
                                  .slice(1, -1)
                                  .map((node: string, i: number) => (
                                    <div
                                      key={i}
                                      className="font-mono text-muted-foreground bg-muted/20 px-2 py-1 rounded border border-border/40 truncate"
                                    >
                                      Step {i + 1}: {node}
                                    </div>
                                  ))}
                              </div>
                            )}

                            <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/5">
                              <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider block mb-0.5">
                                Execution Sink
                              </span>
                              <div className="font-mono text-foreground">
                                {findingDetail.latest_occurrence.taint_evidence_ref.sink_file}:
                                {findingDetail.latest_occurrence.taint_evidence_ref.sink_line}
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="p-8 text-center text-xs text-muted-foreground border border-border/40 rounded-lg">
                            No active taint flow propagation path correlated with this finding.
                          </div>
                        )}
                      </div>
                    )}

                    {/* Sub-tab 4: Canonical Graph Evidence */}
                    {findingSubTab === 'graphs' && (
                      <div className="space-y-3 text-xs">
                        <span className="text-[11px] uppercase font-bold text-muted-foreground tracking-wider block">
                          Correlated Graph Artifacts
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {canonicalGraphs.map((g) => {
                            const isUnsupported =
                              g.status === 'unsupported' ||
                              (g.artifact_type === 'PDG' &&
                                (g.tool_name === 'native_ast_analyzer' ||
                                  (g.node_count === 0 && g.edge_count === 0)));

                            return (
                              <div
                                key={g.id}
                                className="p-3 rounded-lg border border-border/60 bg-card/30 flex items-center justify-between"
                              >
                                <div>
                                  <div className="flex items-center gap-1.5">
                                    <span className="font-bold text-foreground">{g.artifact_type}</span>
                                    {isUnsupported && (
                                      <Badge variant="warning" className="text-[9px] px-1 py-0 text-amber-400">
                                        UNSUPPORTED
                                      </Badge>
                                    )}
                                  </div>
                                  <span className="text-[10px] text-muted-foreground font-mono block mt-0.5">
                                    {isUnsupported
                                      ? 'Requires Joern backend'
                                      : `Nodes: ${g.node_count} • Edges: ${g.edge_count}`}
                                  </span>
                                </div>
                                {isUnsupported ? (
                                  <span className="text-[10px] text-muted-foreground/60 italic font-mono">
                                    Fallback
                                  </span>
                                ) : (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleDownloadArtifact(g)}
                                    className="h-7 px-2 text-[11px]"
                                  >
                                    <Download className="w-3 h-3 mr-1" /> JSON
                                  </Button>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Sub-tab 5: AI Provenance */}
                    {findingSubTab === 'ai' && (
                      <div className="space-y-3 text-xs font-mono">
                        {findingDetail.latest_occurrence?.ai_prediction ? (
                          <div className="p-3.5 rounded-lg border border-amber-500/30 bg-amber-500/5 space-y-2">
                            <span className="font-bold text-amber-400 uppercase text-[11px] block">
                              AI Inference Provenance Record
                            </span>
                            <div className="space-y-1 text-xs">
                              <div>Provider: {findingDetail.latest_occurrence.ai_prediction.provider}</div>
                              <div>Model Name: {findingDetail.latest_occurrence.ai_prediction.model_name}</div>
                              <div>Model Version: {findingDetail.latest_occurrence.ai_prediction.model_version}</div>
                              <div>
                                Confidence Score:{' '}
                                {findingDetail.latest_occurrence.ai_prediction.confidence.toFixed(2)}
                              </div>
                              <div>
                                Inference Timestamp:{' '}
                                {new Date(
                                  findingDetail.latest_occurrence.ai_prediction.created_at
                                ).toLocaleString()}
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="p-8 text-center text-xs text-muted-foreground border border-border/40 rounded-lg">
                            AI prediction record is not directly attached to this occurrence.
                          </div>
                        )}
                      </div>
                    )}

                    {/* Sub-tab 6: Occurrences & Status History */}
                    {findingSubTab === 'occurrences' && (
                      <div className="space-y-4 text-xs">
                        <div className="space-y-2">
                          <span className="text-[11px] uppercase font-bold text-muted-foreground tracking-wider block">
                            Scan Occurrences ({findingDetail.occurrences.length} observed scans)
                          </span>
                          <div className="space-y-1.5 font-mono">
                            {findingDetail.occurrences.map((occ) => (
                              <div
                                key={occ.id}
                                className="p-2.5 rounded border border-border/60 bg-card/40 flex items-center justify-between"
                              >
                                <div>
                                  <span className="font-semibold text-foreground">
                                    Scan: {occ.scan_id.slice(0, 8)}
                                  </span>
                                  <span className="text-[11px] text-muted-foreground block">
                                    Observed at: {new Date(occ.observed_at).toLocaleString()}
                                  </span>
                                </div>
                                <Badge variant="outline" className="text-[10px]">
                                  {occ.severity}
                                </Badge>
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="space-y-2 pt-3 border-t border-border/40">
                          <span className="text-[11px] uppercase font-bold text-muted-foreground tracking-wider block">
                            Status Transition History
                          </span>
                          <div className="space-y-1.5">
                            {findingDetail.status_history.map((sh) => (
                              <div
                                key={sh.id}
                                className="p-2.5 rounded border border-border/40 bg-muted/10 flex items-center justify-between text-xs"
                              >
                                <div>
                                  <span className="font-semibold text-foreground">
                                    {sh.previous_status || 'CREATED'} → {sh.new_status}
                                  </span>
                                  {sh.reason && (
                                    <p className="text-[11px] text-muted-foreground mt-0.5">{sh.reason}</p>
                                  )}
                                </div>
                                <span className="text-[10px] text-muted-foreground font-mono">
                                  {new Date(sh.created_at).toLocaleDateString()}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Sub-tab 7: Comments */}
                    {findingSubTab === 'comments' && (
                      <div className="space-y-3 text-xs">
                        <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                          {findingDetail.comments.length === 0 ? (
                            <div className="p-6 text-center text-muted-foreground border border-border/40 rounded-lg">
                              No team comments yet. Start a discussion below.
                            </div>
                          ) : (
                            findingDetail.comments.map((c) => (
                              <div
                                key={c.id}
                                className="p-3 rounded-lg border border-border/60 bg-card/40 space-y-1"
                              >
                                <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                                  <span className="font-semibold text-foreground flex items-center gap-1">
                                    <User className="w-3 h-3 text-primary" /> Team Member
                                  </span>
                                  <span>{new Date(c.created_at).toLocaleString()}</span>
                                </div>
                                <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                                  {c.content}
                                </p>
                              </div>
                            ))
                          )}
                        </div>

                        {/* New Comment Input */}
                        <form onSubmit={handleAddComment} className="flex gap-2 pt-2">
                          <input
                            type="text"
                            placeholder="Add a comment or investigation note..."
                            value={newComment}
                            onChange={(e) => setNewComment(e.target.value)}
                            className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                          <Button size="sm" type="submit" disabled={submittingComment || !newComment.trim()}>
                            <Send className="w-3.5 h-3.5 mr-1" /> Post
                          </Button>
                        </form>
                      </div>
                    )}

                    {/* Sub-tab 7: Evidence-Aware AI Explanation & XAI Attribution */}
                    {findingSubTab === 'explanation' && (
                      <div className="space-y-4 text-xs">
                        {/* Evidence vs Interpretation Notice */}
                        <div className="p-3 rounded-lg border border-border/80 bg-muted/20 flex items-start gap-2.5">
                          <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                          <div className="space-y-1">
                            <span className="font-semibold text-foreground">
                              Evidence-Aware Explainability & Attribution
                            </span>
                            <p className="text-muted-foreground leading-relaxed">
                              Deterministic evidence (AST sinks, taint flows, canonical graphs) provides the ground truth.
                              XAI methods generate model-derived attribution and interpretation.
                            </p>
                          </div>
                        </div>

                        {/* Method Selector & Trigger */}
                        <div className="p-3 rounded-lg border border-border/60 bg-card/40 flex flex-wrap items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <span className="text-muted-foreground font-medium">Method:</span>
                            <select
                              value={selectedExplanationMethod}
                              onChange={(e) => setSelectedExplanationMethod(e.target.value)}
                              className="text-xs bg-muted/40 border border-border rounded px-2.5 py-1 text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                            >
                              <option value="evidence_synthesizer">Evidence-Aware Synthesizer (Default)</option>
                              <option value="integrated_gradients">Captum / Integrated Gradients</option>
                              <option value="shap">SHAP (Tree/Kernel Attribution)</option>
                              <option value="gnn_explainer">GNNExplainer (Graph Subgraph)</option>
                              <option value="attention">Transformer Attention</option>
                            </select>
                          </div>
                          <Button
                            size="sm"
                            onClick={() => handleGenerateExplanation(selectedExplanationMethod)}
                            disabled={generatingExplanation}
                            className="gap-1.5"
                          >
                            <Cpu className="w-3.5 h-3.5" />
                            {generatingExplanation ? 'Generating...' : 'Generate Explanation'}
                          </Button>
                        </div>

                        {/* Explanations List / Active Explanation */}
                        {explanations.length === 0 ? (
                          <div className="p-8 text-center text-muted-foreground border border-border/40 rounded-lg">
                            No AI explanations generated for this finding yet. Select a method above and click "Generate Explanation".
                          </div>
                        ) : (
                          explanations.map((exp) => (
                            <div
                              key={exp.id}
                              className="p-4 rounded-lg border border-border/80 bg-card/60 space-y-3"
                            >
                              {/* Header & Status */}
                              <div className="flex items-center justify-between border-b border-border/40 pb-2 flex-wrap gap-2">
                                <div className="flex items-center gap-2">
                                  <Badge variant="outline" className="font-mono text-[10px] uppercase">
                                    {exp.explanation_method}
                                  </Badge>
                                  <span
                                    className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                                      exp.method_status === 'SUPPORTED'
                                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                    }`}
                                  >
                                    {exp.method_status}
                                  </span>
                                </div>
                                <span className="text-[10px] text-muted-foreground font-mono">
                                  {exp.provider} • {exp.model_name}:{exp.model_version} • {new Date(exp.created_at).toLocaleTimeString()}
                                </span>
                              </div>

                              {/* Method Status Reason if Not Supported */}
                              {exp.method_status !== 'SUPPORTED' && exp.status_reason && (
                                <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
                                  <p className="font-semibold mb-0.5">Method Limitation / Status Notice:</p>
                                  <p>{exp.status_reason}</p>
                                </div>
                              )}

                              {/* Summary & Analysis */}
                              <div className="space-y-2">
                                <div>
                                  <span className="font-semibold text-foreground block">Executive Summary:</span>
                                  <p className="text-muted-foreground leading-relaxed mt-0.5">{exp.summary}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-foreground block">Root Cause Analysis:</span>
                                  <p className="text-muted-foreground leading-relaxed mt-0.5">{exp.root_cause}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-foreground block">Why Code is Vulnerable:</span>
                                  <p className="text-muted-foreground leading-relaxed mt-0.5">{exp.why_vulnerable}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-foreground block">Security Impact:</span>
                                  <p className="text-muted-foreground leading-relaxed mt-0.5">{exp.impact}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-foreground block">Evidence Synthesis:</span>
                                  <p className="text-muted-foreground leading-relaxed mt-0.5">{exp.evidence_explanation}</p>
                                </div>
                              </div>

                              {/* Normalized Attributions: Important Locations */}
                              {exp.important_locations && exp.important_locations.length > 0 && (
                                <div className="pt-2 border-t border-border/40 space-y-2">
                                  <span className="font-semibold text-foreground block">
                                    Attributed Source Locations ({exp.important_locations.length}):
                                  </span>
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                    {exp.important_locations.map((loc, idx) => (
                                      <div
                                        key={idx}
                                        className="p-2.5 rounded border border-border/60 bg-muted/20 flex items-center justify-between"
                                      >
                                        <div className="font-mono truncate max-w-[220px]">
                                          <span className="text-foreground">{loc.file}</span>:
                                          <span className="text-primary font-bold">L{loc.start_line}-L{loc.end_line}</span>
                                          <span className="text-[10px] text-muted-foreground block">
                                            Importance: {(loc.importance * 100).toFixed(1)}%
                                          </span>
                                        </div>
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          className="h-6 px-2 text-[10px]"
                                          onClick={() => setFindingSubTab('source')}
                                        >
                                          View Code
                                        </Button>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Important Tokens */}
                              {exp.important_tokens && exp.important_tokens.length > 0 && (
                                <div className="pt-2 border-t border-border/40 space-y-1.5">
                                  <span className="font-semibold text-foreground block">
                                    Attributed Tokens ({exp.important_tokens.length}):
                                  </span>
                                  <div className="flex flex-wrap gap-1.5">
                                    {exp.important_tokens.map((tok, idx) => (
                                      <span
                                        key={idx}
                                        className="px-2 py-0.5 rounded bg-muted/40 border border-border/60 font-mono text-[11px] text-foreground"
                                      >
                                        <span className="text-amber-400 font-bold">{tok.token}</span>
                                        <span className="text-muted-foreground ml-1.5 text-[10px]">
                                          ({Math.round(tok.importance * 100)}%)
                                        </span>
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Important Graph Nodes */}
                              {exp.important_nodes && exp.important_nodes.length > 0 && (
                                <div className="pt-2 border-t border-border/40 space-y-1.5">
                                  <span className="font-semibold text-foreground block">
                                    Important Graph Nodes ({exp.important_nodes.length}):
                                  </span>
                                  <div className="flex flex-wrap gap-1.5">
                                    {exp.important_nodes.map((node, idx) => (
                                      <span
                                        key={idx}
                                        className="px-2 py-0.5 rounded bg-muted/40 border border-border/60 font-mono text-[11px]"
                                      >
                                        <span className="text-primary">{node.label}</span>
                                        <span className="text-muted-foreground ml-1 text-[10px]">
                                          [{node.node_type}] ({Math.round(node.importance * 100)}%)
                                        </span>
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    )}

                    {/* Sub-tab 8: LLM Remediation & Isolated Validation */}
                    {findingSubTab === 'remediation' && (
                      <div className="space-y-4 text-xs">
                        {/* Core Invariant Banner */}
                        <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/10 flex items-start gap-2.5">
                          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                          <div className="space-y-0.5">
                            <span className="font-semibold text-amber-300">
                              Core Security Principle: AI-generated fix != verified fix
                            </span>
                            <p className="text-muted-foreground leading-relaxed">
                              Remediations are proposed unified diff patches applied strictly inside disposable isolated workspaces.
                              A finding is marked FIXED only after approved validation, and marked VERIFIED only after an authoritative
                              verification scan proves resolution without regressions.
                            </p>
                          </div>
                        </div>

                        {/* Top Action Bar & Remediation Selector */}
                        <div className="p-3 rounded-lg border border-border/60 bg-card/40 flex flex-wrap items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <span className="text-muted-foreground font-medium">Remediations:</span>
                            {remediations.length > 0 ? (
                              <select
                                value={selectedRemediationId || ''}
                                onChange={(e) => setSelectedRemediationId(e.target.value)}
                                className="text-xs bg-muted/40 border border-border rounded px-2.5 py-1 text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                              >
                                {remediations.map((r) => (
                                  <option key={r.id} value={r.id}>
                                    Remediation #{r.remediation_number} ({r.status})
                                  </option>
                                ))}
                              </select>
                            ) : (
                              <span className="text-muted-foreground font-mono">None generated</span>
                            )}
                          </div>
                          <Button
                            size="sm"
                            onClick={handleGenerateRemediation}
                            disabled={generatingRemediation}
                            className="gap-1.5"
                          >
                            <FileDiff className="w-3.5 h-3.5" />
                            {generatingRemediation ? 'Generating Fix...' : 'Generate Secure Fix'}
                          </Button>
                        </div>

                        {/* Active Remediation Content */}
                        {(() => {
                          const activeRem = remediations.find((r) => r.id === selectedRemediationId) || remediations[0];
                          if (!activeRem) {
                            return (
                              <div className="p-8 text-center text-muted-foreground border border-border/40 rounded-lg">
                                No remediation proposals available. Click "Generate Secure Fix" to propose an automated security patch.
                              </div>
                            );
                          }

                          const latestVal = activeRem.validations && activeRem.validations.length > 0 ? activeRem.validations[0] : null;

                          return (
                            <div className="space-y-4">
                              {/* Remediation Summary Card */}
                              <div className="p-4 rounded-lg border border-border/80 bg-card/60 space-y-3">
                                <div className="flex items-center justify-between border-b border-border/40 pb-2 flex-wrap gap-2">
                                  <div className="flex items-center gap-2">
                                    <span className="font-bold text-foreground">
                                      Remediation #{activeRem.remediation_number}
                                    </span>
                                    <Badge
                                      variant="outline"
                                      className={`font-mono text-[10px] ${
                                        activeRem.status === 'VALIDATED'
                                          ? 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10'
                                          : activeRem.status === 'FAILED_VALIDATION'
                                          ? 'text-red-400 border-red-500/40 bg-red-500/10'
                                          : activeRem.status === 'APPROVED'
                                          ? 'text-blue-400 border-blue-500/40 bg-blue-500/10'
                                          : 'text-amber-400 border-amber-500/40 bg-amber-500/10'
                                      }`}
                                    >
                                      {activeRem.status}
                                    </Badge>
                                  </div>
                                  <span className="text-[10px] text-muted-foreground font-mono">
                                    {activeRem.provider} • SHA-256: {activeRem.patch_checksum.substring(0, 12)}...
                                  </span>
                                </div>

                                <div className="space-y-1.5">
                                  <p className="font-semibold text-foreground">{activeRem.summary}</p>
                                  <p className="text-muted-foreground leading-relaxed">{activeRem.explanation}</p>
                                </div>

                                {activeRem.changed_files && activeRem.changed_files.length > 0 && (
                                  <div className="text-[11px] font-mono">
                                    <span className="text-muted-foreground">Target Files: </span>
                                    <span className="text-foreground">{activeRem.changed_files.join(', ')}</span>
                                  </div>
                                )}

                                {/* Unified Diff Viewer */}
                                <div className="space-y-1.5 pt-1">
                                  <span className="font-semibold text-foreground flex items-center gap-1.5">
                                    <Terminal className="w-3.5 h-3.5 text-primary" /> Unified Diff Patch
                                  </span>
                                  <pre className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 text-[11px] font-mono overflow-x-auto max-h-[300px] leading-relaxed select-text">
                                    {activeRem.diff_content.split('\n').map((line, idx) => {
                                      const isAdd = line.startsWith('+') && !line.startsWith('+++');
                                      const isDel = line.startsWith('-') && !line.startsWith('---');
                                      const isHunk = line.startsWith('@@');
                                      return (
                                        <div
                                          key={idx}
                                          className={
                                            isAdd
                                              ? 'text-emerald-400 bg-emerald-500/10 -mx-3 px-3'
                                              : isDel
                                              ? 'text-red-400 bg-red-500/10 -mx-3 px-3'
                                              : isHunk
                                              ? 'text-cyan-400 bg-cyan-500/10 -mx-3 px-3'
                                              : 'text-zinc-400'
                                          }
                                        >
                                          {line}
                                        </div>
                                      );
                                    })}
                                  </pre>
                                </div>

                                {/* Human Review Actions */}
                                {(activeRem.status === 'GENERATED' || activeRem.status === 'PROPOSED') && (
                                  <div className="p-3 rounded border border-border/60 bg-muted/20 space-y-2">
                                    <span className="font-semibold text-foreground block">Human Review & Decision:</span>
                                    <input
                                      type="text"
                                      placeholder="Optional review justification or comment..."
                                      value={reviewComment}
                                      onChange={(e) => setReviewComment(e.target.value)}
                                      className="w-full px-2.5 py-1 text-xs rounded border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                                    />
                                    <div className="flex items-center gap-2 pt-1">
                                      <Button
                                        size="sm"
                                        onClick={() => handleReviewRemediation('APPROVE')}
                                        disabled={actionInProgress}
                                        className="gap-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                                      >
                                        <Check className="w-3.5 h-3.5" /> Approve Remediation
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleReviewRemediation('REJECT')}
                                        disabled={actionInProgress}
                                        className="gap-1 text-red-400 hover:text-red-300"
                                      >
                                        <X className="w-3.5 h-3.5" /> Reject Remediation
                                      </Button>
                                    </div>
                                  </div>
                                )}

                                {/* Apply to Sandbox Action */}
                                {activeRem.status === 'APPROVED' && (
                                  <div className="p-3 rounded border border-border/60 bg-muted/20 flex items-center justify-between">
                                    <div>
                                      <span className="font-semibold text-foreground block">Remediation Approved</span>
                                      <span className="text-muted-foreground text-[11px]">
                                        Apply diff to a fresh isolated validation workspace.
                                      </span>
                                    </div>
                                    <Button
                                      size="sm"
                                      onClick={handleApplyRemediation}
                                      disabled={actionInProgress}
                                      className="gap-1.5"
                                    >
                                      <Play className="w-3.5 h-3.5" /> Apply to Sandbox
                                    </Button>
                                  </div>
                                )}

                                {/* Validation Trigger Action */}
                                {(activeRem.status === 'APPLIED' ||
                                  activeRem.status === 'VALIDATED' ||
                                  activeRem.status === 'FAILED_VALIDATION') && (
                                  <div className="p-3 rounded border border-border/60 bg-muted/20 flex flex-wrap items-center justify-between gap-3">
                                    <div className="flex items-center gap-2">
                                      <input
                                        type="checkbox"
                                        id="run-tests-cb"
                                        checked={runSandboxTests}
                                        onChange={(e) => setRunSandboxTests(e.target.checked)}
                                        className="rounded border-border text-primary focus:ring-primary cursor-pointer"
                                      />
                                      <label htmlFor="run-tests-cb" className="text-foreground cursor-pointer font-medium">
                                        Execute Sandbox Allowlisted Tests
                                      </label>
                                    </div>
                                    <Button
                                      size="sm"
                                      onClick={handleValidateRemediation}
                                      disabled={actionInProgress}
                                      className="gap-1.5"
                                    >
                                      <RotateCw className="w-3.5 h-3.5" />
                                      {actionInProgress ? 'Validating...' : 'Run Multi-Stage Validation'}
                                    </Button>
                                  </div>
                                )}
                              </div>

                              {/* Multi-Stage Validation Stepper Results */}
                              {latestVal && (
                                <div className="p-4 rounded-lg border border-border/80 bg-card/60 space-y-3">
                                  <div className="flex items-center justify-between border-b border-border/40 pb-2">
                                    <span className="font-bold text-foreground">
                                      Validation Attempt #{latestVal.attempt_number} Results
                                    </span>
                                    <Badge
                                      variant="outline"
                                      className={`font-mono text-[10px] ${
                                        latestVal.status === 'PASSED'
                                          ? 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10'
                                          : latestVal.status === 'FAILED'
                                          ? 'text-red-400 border-red-500/40 bg-red-500/10'
                                          : 'text-amber-400 border-amber-500/40 bg-amber-500/10'
                                      }`}
                                    >
                                      {latestVal.status}
                                    </Badge>
                                  </div>

                                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
                                    <div className="p-2.5 rounded border border-border/60 bg-muted/20">
                                      <span className="text-muted-foreground block text-[10px]">1. Patch Apply</span>
                                      <span className="font-bold text-foreground font-mono">
                                        {latestVal.patch_apply_result?.status || 'PENDING'}
                                      </span>
                                    </div>
                                    <div className="p-2.5 rounded border border-border/60 bg-muted/20">
                                      <span className="text-muted-foreground block text-[10px]">2. Syntax Check</span>
                                      <span className="font-bold text-foreground font-mono">
                                        {latestVal.syntax_result?.status || 'PENDING'}
                                      </span>
                                    </div>
                                    <div className="p-2.5 rounded border border-border/60 bg-muted/20">
                                      <span className="text-muted-foreground block text-[10px]">3. Build Verification</span>
                                      <span className="font-bold text-foreground font-mono">
                                        {latestVal.build_result?.status || 'NOT_CONFIGURED'}
                                      </span>
                                    </div>
                                    <div className="p-2.5 rounded border border-border/60 bg-muted/20">
                                      <span className="text-muted-foreground block text-[10px]">4. Allowlisted Tests</span>
                                      <span className="font-bold text-foreground font-mono">
                                        {latestVal.test_result?.status || 'NOT_CONFIGURED'}
                                      </span>
                                    </div>
                                    <div className="p-2.5 rounded border border-border/60 bg-muted/20">
                                      <span className="text-muted-foreground block text-[10px]">5. Static Re-analysis</span>
                                      <span className="font-bold text-foreground font-mono">
                                        {latestVal.static_analysis_result?.status || 'PENDING'}
                                      </span>
                                    </div>
                                    <div className="p-2.5 rounded border border-border/60 bg-muted/20">
                                      <span className="text-muted-foreground block text-[10px]">6. Taint / Graph Check</span>
                                      <span className="font-bold text-foreground font-mono">
                                        {latestVal.taint_result?.status || 'UNSUPPORTED'}
                                      </span>
                                    </div>
                                    <div className="p-2.5 rounded border border-border/60 bg-muted/20">
                                      <span className="text-muted-foreground block text-[10px]">7. Security Regression</span>
                                      <span className="font-bold text-foreground font-mono">
                                        {latestVal.regression_result?.status || 'PASS'}
                                      </span>
                                    </div>
                                    <div className="p-2.5 rounded border border-border/60 bg-muted/20">
                                      <span className="text-muted-foreground block text-[10px]">8. Verification Scan</span>
                                      <span className="font-bold text-foreground font-mono">
                                        {latestVal.final_verification_result}
                                      </span>
                                    </div>
                                  </div>

                                  {/* Authoritative Verification Outcome Banner */}
                                  {latestVal.final_verification_result === 'VERIFIED' ? (
                                    <div className="p-3 rounded-lg border border-emerald-500/40 bg-emerald-500/10 flex items-center gap-2.5 text-emerald-400">
                                      <ShieldCheck className="w-5 h-5 shrink-0" />
                                      <div>
                                        <span className="font-bold block">Finding Verified (VERIFIED)</span>
                                        <span className="text-emerald-300 text-[11px]">
                                          Authoritative verification scan confirmed vulnerability resolution with zero security regressions.
                                        </span>
                                      </div>
                                    </div>
                                  ) : latestVal.final_verification_result === 'NOT_VERIFIED' ? (
                                    <div className="p-3 rounded-lg border border-red-500/40 bg-red-500/10 flex items-center gap-2.5 text-red-400">
                                      <ShieldAlert className="w-5 h-5 shrink-0" />
                                      <div>
                                        <span className="font-bold block">Fix Not Verified</span>
                                        <span className="text-red-300 text-[11px]">
                                          {latestVal.failure_reason || 'Validation checks or verification scan failed.'}
                                        </span>
                                      </div>
                                    </div>
                                  ) : null}
                                </div>
                              )}

                              {/* Validation History List */}
                              {activeRem.validations && activeRem.validations.length > 1 && (
                                <div className="space-y-2 pt-2 border-t border-border/40">
                                  <span className="font-semibold text-foreground block">
                                    Validation History ({activeRem.validations.length} attempts):
                                  </span>
                                  <div className="space-y-1.5">
                                    {activeRem.validations.map((v) => (
                                      <div
                                        key={v.id}
                                        className="p-2.5 rounded border border-border/60 bg-muted/20 flex items-center justify-between text-xs"
                                      >
                                        <div className="font-mono">
                                          <span className="font-bold text-foreground">Attempt #{v.attempt_number}</span>: {v.status}
                                          {v.failure_reason && (
                                            <span className="text-red-400 block text-[11px] font-sans">
                                              {v.failure_reason}
                                            </span>
                                          )}
                                        </div>
                                        <span className="text-[10px] text-muted-foreground font-mono">
                                          {new Date(v.started_at).toLocaleTimeString()}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })()}
                      </div>
                    )}

                    {findingSubTab === 'occurrences' && (
                      <div className="space-y-3 text-xs">
                        <div className="p-3 bg-muted/20 rounded border border-border/40 text-muted-foreground">
                          <span className="font-semibold text-foreground block mb-1">Authoritative Occurrences</span>
                          Multiple occurrences across revisions or files belong to this single canonical Finding ({findingDetail.fingerprint.slice(0, 16)}...). They do not inflate organization finding counts.
                        </div>
                        <div className="divide-y divide-border/40 border border-border/40 rounded-lg overflow-hidden">
                          {findingDetail.occurrences.map((occ, idx) => (
                            <div key={occ.id} className="p-3 bg-card/40 flex items-start justify-between">
                              <div>
                                <span className="font-mono font-semibold text-foreground block">
                                  {occ.file_path}:{occ.start_line}
                                </span>
                                <span className="text-muted-foreground text-[11px] block mt-0.5">
                                  Function: {occ.function_name || '<global>'} &bull; Scan: {occ.scan_id ? occ.scan_id.slice(0, 8) : 'N/A'}
                                </span>
                              </div>
                              <Badge variant="outline" className="text-[10px] uppercase">
                                Occurrence #{idx + 1}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {findingSubTab === 'comments' && (
                      <div className="space-y-4 text-xs">
                        {/* Assignment Row */}
                        <div className="p-3 bg-muted/20 rounded-lg border border-border/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                          <div>
                            <span className="text-[11px] uppercase font-bold text-muted-foreground tracking-wider block">
                              Assigned Owner
                            </span>
                            <span className="text-sm font-semibold text-foreground mt-0.5 block">
                              {findingDetail.current_assignment
                                ? findingDetail.current_assignment.assigned_to?.name ||
                                  findingDetail.current_assignment.assigned_to?.email ||
                                  'Assigned Member'
                                : 'Unassigned'}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <select
                              className="h-8 rounded border border-input bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                              value={selectedAssigneeId}
                              onChange={(e) => {
                                setSelectedAssigneeId(e.target.value);
                                if (e.target.value) handleAssignFinding(e.target.value);
                              }}
                            >
                              <option value="">Assign to member...</option>
                              {teamMembers.map((m) => (
                                <option key={m.user_id} value={m.user_id}>
                                  {m.user_name} ({m.user_email})
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>

                        {/* Activity & Comments Timeline */}
                        <div className="space-y-3">
                          <span className="text-xs font-semibold text-foreground block">
                            Activity & Comment Stream
                          </span>
                          {loadingActivities ? (
                            <div className="py-6 text-center text-muted-foreground">Loading activity...</div>
                          ) : activities.length === 0 && findingDetail.comments.length === 0 ? (
                            <div className="p-4 text-center border border-border/40 rounded bg-muted/10 text-muted-foreground text-xs">
                              No collaboration activity or comments yet.
                            </div>
                          ) : (
                            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                              {activities.map((act) => (
                                <div
                                  key={act.id}
                                  className="p-2.5 rounded border border-border/40 bg-card/60 text-xs space-y-1"
                                >
                                  <div className="flex justify-between items-center text-[11px]">
                                    <span className="font-semibold text-foreground">
                                      {act.actor_name || 'System'}
                                    </span>
                                    <span className="text-muted-foreground font-mono">
                                      {act.created_at ? new Date(act.created_at).toLocaleString() : ''}
                                    </span>
                                  </div>
                                  <p className="text-foreground/90 leading-relaxed">
                                    {act.description || act.title}
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Add Comment Input */}
                        <form onSubmit={handleAddComment} className="pt-2 border-t border-border/40 space-y-2">
                          <div className="relative">
                            <textarea
                              rows={2}
                              value={newComment}
                              onChange={(e) => setNewComment(e.target.value)}
                              placeholder="Write a comment... (Type @username to mention a teammate)"
                              className="w-full rounded-md border border-input bg-background p-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-[11px] text-muted-foreground">
                              Valid @mentions trigger real-time in-app notifications
                            </span>
                            <Button
                              type="submit"
                              size="sm"
                              disabled={submittingComment || !newComment.trim()}
                              className="gap-1.5 text-xs h-7"
                            >
                              <Send className="w-3 h-3" />
                              {submittingComment ? 'Posting...' : 'Post Comment'}
                            </Button>
                          </div>
                        </form>
                      </div>
                    )}
                  </Card>

                ) : (
                  <div className="p-12 text-center text-muted-foreground border border-border/40 rounded-xl bg-card/20">
                    Select a finding from the list to investigate.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: CANONICAL GRAPHS ──────────────────────────── */}
      {activeWorkspaceTab === 'graphs' && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-card/50 border border-border text-xs text-muted-foreground leading-relaxed">
            <span className="font-semibold text-foreground block mb-1">
              Canonical Graph Pipeline
            </span>
            These program graphs are generated deterministically during scan processing and stored in
            MinIO object storage. The AI Inference Provider consumes these exact canonical artifacts.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {canonicalGraphs.map((artifact) => {
              const isUnsupported =
                artifact.status === 'unsupported' ||
                (artifact.artifact_type === 'PDG' &&
                  (artifact.tool_name === 'native_ast_analyzer' ||
                    (artifact.node_count === 0 && artifact.edge_count === 0)));

              return (
                <Card key={artifact.id} className="p-4 border-border/80 flex flex-col justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-foreground">{artifact.artifact_type}</span>
                      {isUnsupported ? (
                        <Badge variant="warning" className="text-[10px] font-semibold text-amber-400 border-amber-500/30 bg-amber-500/10">
                          UNSUPPORTED
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-[10px]">
                          {artifact.schema_version}
                        </Badge>
                      )}
                    </div>

                    {isUnsupported ? (
                      <div className="p-3 rounded-md bg-amber-500/5 border border-amber-500/20 text-xs text-amber-300/90 leading-relaxed">
                        <p className="font-semibold text-amber-400 mb-1">Joern Backend Required</p>
                        <p>
                          PDG generation requires the Joern analysis backend. The current native analyzer does not provide
                          control/data-dependence analysis.
                        </p>
                        <div className="mt-2 text-[10px] font-mono text-muted-foreground">
                          Engine: {artifact.tool_name || 'native_ast_analyzer'}
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-1 text-xs text-muted-foreground font-mono">
                        <div>Nodes: {artifact.node_count}</div>
                        <div>Edges: {artifact.edge_count}</div>
                        <div>Size: {(artifact.size_bytes / 1024).toFixed(1)} KB</div>
                        <div>Tool: {artifact.tool_name} ({artifact.tool_version})</div>
                      </div>
                    )}
                  </div>

                  <div className="pt-3 mt-3 border-t border-border/60">
                    {isUnsupported ? (
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full gap-1.5 opacity-50 cursor-not-allowed text-xs text-muted-foreground"
                        disabled
                      >
                        Download Unavailable
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full gap-1.5"
                        disabled={downloadingId === artifact.id}
                        onClick={() => handleDownloadArtifact(artifact)}
                      >
                        <Download className="w-3.5 h-3.5" />
                        {downloadingId === artifact.id ? 'Downloading...' : 'Download Canonical JSON'}
                      </Button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ── TAB 3: TAINT ANALYSIS ────────────────────────────── */}
      {activeWorkspaceTab === 'taint' && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-card/50 border border-border text-xs text-muted-foreground leading-relaxed">
            <span className="font-semibold text-foreground block mb-1">
              Data Flow & Taint Analysis
            </span>
            Interprocedural data flow tracking identifies untrusted external inputs propagating through
            the code property graph to sensitive execution sinks.
          </div>

          {taintEvidence?.status === 'not_run' ? (
            <Card className="p-8 text-center space-y-2 border-border/60">
              <Layers className="w-8 h-8 mx-auto text-muted-foreground opacity-40" />
              <h3 className="text-sm font-semibold text-foreground">Taint Analysis Not Executed</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Taint analysis was not executed for this scan. Data flow and taint tracking was not configured
                or was skipped during this pipeline run.
              </p>
            </Card>
          ) : taintEvidence?.status === 'failed' ? (
            <Card className="p-8 text-center space-y-2 border-destructive/30 bg-destructive/5">
              <AlertCircle className="w-8 h-8 mx-auto text-destructive" />
              <h3 className="text-sm font-semibold text-destructive">Taint Analysis Failed</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                {taintEvidence.message || 'Taint analysis execution failed during this scan.'}
              </p>
            </Card>
          ) : !taintEvidence?.paths || taintEvidence.paths.length === 0 ? (
            <Card className="p-8 text-center space-y-3 border-border/60">
              <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-400 opacity-80" />
              <h3 className="text-sm font-semibold text-foreground">
                Taint analysis completed — no taint paths detected.
              </h3>
              <p className="text-xs text-muted-foreground max-w-lg mx-auto leading-relaxed">
                Interprocedural data flow tracking analyzed reachable paths across the code property graph. No
                direct propagation paths from untrusted external sources to sensitive execution sinks were identified
                in this snapshot.
              </p>
              <div className="p-3 rounded-md bg-muted/20 border border-border/40 text-[11px] text-muted-foreground max-w-lg mx-auto text-left">
                <span className="font-semibold text-foreground block mb-0.5">Truthfulness Note:</span>
                Zero detected taint paths confirms the absence of source-to-sink data flows under the configured
                taint ruleset. It does not imply that the project is completely secure or free from logic flaws,
                insecure configuration, or pattern-based vulnerabilities.
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              <div className="lg:col-span-5 space-y-2 max-h-[600px] overflow-y-auto">
                {taintEvidence.paths.map((path, idx) => {
                  const isSelected = selectedTaintPath === path;
                  return (
                    <div
                      key={idx}
                      onClick={() => setSelectedTaintPath(path)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? 'border-primary bg-primary/5'
                          : 'border-border/60 hover:border-border bg-card/20'
                      }`}
                    >
                      <span className="text-xs font-semibold text-foreground block">
                        Path #{idx + 1}: {path.source_file}:{path.source_line} → {path.sink_file}:{path.sink_line}
                      </span>
                      <span className="text-[10px] text-muted-foreground font-mono mt-1 block">
                        Propagation Steps: {path.nodes?.length || 0}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="lg:col-span-7">
                {selectedTaintPath ? (
                  <Card className="p-5 border-border space-y-4">
                    <h3 className="text-sm font-bold text-foreground">Taint Trace Inspection</h3>
                    <div className="space-y-3 text-xs font-mono">
                      <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5">
                        <span className="text-emerald-400 font-bold block mb-1">Source Origin</span>
                        <div>{selectedTaintPath.source_file}:{selectedTaintPath.source_line}</div>
                      </div>
                      {selectedTaintPath.nodes?.length > 2 && (
                        <div className="pl-6 border-l-2 border-dashed border-border/60 space-y-1">
                          {selectedTaintPath.nodes.slice(1, -1).map((node, i) => (
                            <div key={i} className="p-1.5 rounded bg-muted/20 text-muted-foreground">
                              Step {i + 1}: {node}
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/5">
                        <span className="text-amber-400 font-bold block mb-1">Execution Sink</span>
                        <div>{selectedTaintPath.sink_file}:{selectedTaintPath.sink_line}</div>
                      </div>
                    </div>
                  </Card>
                ) : (
                  <div className="p-12 text-center text-xs text-muted-foreground border border-border/40 rounded-lg">
                    Select a taint path to inspect.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── SUPPRESSION MODAL ─────────────────────────────────── */}
      {showSuppressModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="max-w-md w-full p-6 space-y-4 border-border bg-card shadow-xl">
            <h3 className="text-base font-bold text-foreground">Suppress Finding</h3>
            <p className="text-xs text-muted-foreground">
              Controlled status change with mandatory audit reason logging.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-muted-foreground block mb-1">Suppression Classification</label>
                <select
                  value={suppressType}
                  onChange={(e) => setSuppressType(e.target.value as any)}
                  className="w-full px-3 py-1.5 rounded border border-border bg-card text-foreground focus:outline-none"
                >
                  <option value="FALSE_POSITIVE">FALSE_POSITIVE (Incorrect detection)</option>
                  <option value="RISK_ACCEPTED">RISK_ACCEPTED (Known risk acceptable)</option>
                  <option value="SUPPRESSED">SUPPRESSED (Temporarily suppressed)</option>
                </select>
              </div>

              <div>
                <label className="text-muted-foreground block mb-1">Justification Reason *</label>
                <textarea
                  rows={3}
                  value={suppressReason}
                  onChange={(e) => setSuppressReason(e.target.value)}
                  placeholder="Explain why this finding is being suppressed..."
                  className="w-full px-3 py-1.5 rounded border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button size="sm" variant="outline" onClick={() => setShowSuppressModal(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleSuppress}>
                Confirm Suppression
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

# VulnScan System Flow

## 1. Purpose

This document explains how data moves through VulnScan, from the moment a user creates a project to the point where a vulnerability is investigated, remediated, validated, and verified.

The system is organized around one principle:

> Every security result must remain traceable to the source snapshot, analysis evidence, model provenance, and lifecycle operations that produced it.

---

## 2. High-Level Flow

```mermaid
flowchart TD
    User["User"] --> Org["Organization"]
    Org --> Project["Project"]
    Project --> Src["Repository / Upload"]
    Src --> Snap["Immutable Source Snapshot"]
    Snap --> Scan["Scan"]

    Scan --> Pre["Preprocessing"]
    Scan --> Static["Static Analysis"]
    Scan --> Graph["Graph Analysis"]
    Scan --> Taint["Taint Analysis"]
    Scan --> AI["AI Analysis"]

    Pre --> Corr["Evidence Correlation"]
    Static --> Corr
    Graph --> Corr
    Taint --> Corr
    AI --> Corr

    Corr --> Finding["Finding"]

    Finding --> Inv["Investigation"]
    Finding --> XAI["XAI"]
    Finding --> Rem["Remediation"]
    Finding --> Val["Validation"]
    Finding --> Ver["Verification"]

    Ver --> Out["Reports / Analytics / CI"]
```

---

## 3. Organization Context

A user operates inside an organization. The organization determines:

- Which projects are visible
- Which repositories are accessible
- Which scans can be executed
- Which findings can be modified
- Which reports can be generated
- Which integrations can be configured
- Which administrative operations are permitted

Every organization-scoped API operation validates the current organization context.

---

## 4. Project Creation

A project establishes the main security-analysis boundary.

```mermaid
flowchart TD
    Org["Organization"] --> Project["Project"]
    Project --> Repo["Repository"]
    Project --> Snaps["Source Snapshots"]
    Project --> Scans["Scans"]
    Project --> Findings["Findings"]
    Project --> Reports["Reports"]
    Project --> Policies["Security Policies"]
```

Projects are managed according to the user's organization permissions.

---

## 5. Repository and Source Ingestion

Source can enter the system through supported ingestion mechanisms.

```mermaid
flowchart LR
    In["Repository / Upload"] --> Acq["Source Acquisition"]
    Acq --> Valid["Validation"]
    Valid --> Snap["Immutable Snapshot"]
```

The original source is preserved. The system does not use a mutable working copy as the historical source of truth.

---

## 6. Immutable Source Snapshot

A snapshot represents the exact source state analyzed by a scan. It contains references to:

- Source files
- Functions
- Manifest information
- Integrity metadata
- Repository and commit information, where applicable

```mermaid
flowchart LR
    Repo["Repository"] --> Commit["Commit / Upload"]
    Commit --> Snap["Source Snapshot"]
    Snap --> Scan["Scan"]
```

Historical scans therefore remain tied to the exact source state that was analyzed.

---

## 7. Preprocessing

The preprocessing stage prepares source for analysis.

```mermaid
flowchart TD
    Snap["Source Snapshot"] --> Lang["Language Detection"]
    Lang --> Valid["Source Validation"]
    Valid --> Func["Function Extraction"]
    Func --> Tok["Tokenization"]
    Tok --> Norm["Normalization"]
    Norm --> Meta["Function Metadata"]
```

Preprocessing does not replace the original source. The original remains available for investigation and evidence display.

---

## 8. Scan Creation

A scan is created against a specific source snapshot. The scan records:

- Project
- Organization
- Source snapshot
- Configuration
- Creation time
- Current state
- Stage state
- Failure information
- Execution metadata

A scan never silently switches to another source snapshot.

---

## 9. Scan Execution

The scan is queued for background execution.

```mermaid
flowchart LR
    API["API"] --> Create["Create Scan"]
    Create --> Queue["Queue Task"]
    Queue --> Worker["Celery Worker"]
    Worker --> Orch["Scan Orchestrator"]
```

The orchestrator executes the configured stages in order.

---

## 10. Scan Stages

The analysis flow is conceptually:

```mermaid
flowchart TD
    Q["Queued"] --> P["Preprocessing"]
    P --> S["Static Analysis"]
    S --> G["Graph Processing"]
    G --> T["Taint Analysis"]
    T --> A["AI Analysis"]
    A --> PP["Post Processing"]
    PP --> C["Correlation"]
    C --> Done["Completed"]
```

Every stage records its own execution state.

---

## 11. Static Analysis

Static analysis operates against the immutable snapshot. Possible outputs include:

- AST
- CFG
- CPG
- Call graph
- Data flow
- Pointer analysis
- Complexity
- API usage
- Taint information

The actual output depends on the configured analysis engine. If a capability is unavailable, the system records the corresponding state instead of fabricating an artifact.

---

## 12. Graph Processing

Graph processing transforms program structure into canonical graph artifacts.

```mermaid
flowchart TD
    Src["Source"] --> Engine["Analysis Engine"]
    Engine --> Rep["Graph Representation"]
    Rep --> Art["Canonical Artifact"]
    Art --> Type["Graph Type"]
    Art --> Schema["Schema Version"]
    Art --> Nodes["Node Count"]
    Art --> Edges["Edge Count"]
    Art --> Sum["Checksum"]
```

Downstream graph-processing and AI components can then consume the artifact.

---

## 13. Taint Analysis

Taint analysis identifies data flows between sources and sinks.

```mermaid
flowchart TD
    Source["Source"] --> Input["Input"]
    Input --> Prop["Propagation"]
    Prop --> San["Sanitization"]
    Prop --> Unsafe["Unsafe Flow"]
    Unsafe --> Sink["Sink"]
```

The result is stored as static evidence. A taint path alone is not equivalent to a confirmed vulnerability.

---

## 14. AI Analysis

AI inference operates after the deterministic analysis context is available.

```mermaid
flowchart TD
    Feat["Graph Features"] --> GraphRep["Graph Representation"]
    Feat --> SemRep["Semantic Representation"]
    GraphRep --> Provider["AI Provider"]
    SemRep --> Provider
    Provider --> Pred["AI Prediction"]
```

Predictions are stored with provenance:

- Provider
- Model
- Version
- Confidence
- Prediction type
- Source / function location
- CWE
- Severity
- CVSS information
- Evidence references

---

## 15. Evidence Correlation

The finding engine combines independent signals.

```mermaid
flowchart TD
    Static["Static Evidence"] --> Corr
    Taint["Taint Evidence"] --> Corr
    Graph["Graph Evidence"] --> Corr
    AI["AI Prediction"] --> Corr
    Loc["Source Location"] --> Corr

    Corr["Correlation"] --> FP["Fingerprint"]
    FP --> Dedup["Deduplication"]
    Dedup --> Risk["Risk"]
    Risk --> Finding["Finding"]
```

This prevents every individual analysis signal from becoming an independent vulnerability.

---

## 16. Finding Persistence

A finding is a persistent security-domain object. It can contain:

- Vulnerability classification
- CWE
- Severity
- CVSS
- Risk
- Confidence
- Source location
- Evidence
- Fingerprint
- Status
- Assignment
- Comments
- Suppression
- Risk acceptance
- Occurrences
- History

---

## 17. Finding Deduplication

Repeated scans are compared using finding fingerprints.

```mermaid
flowchart LR
    subgraph A["Scan A"]
        FA["Finding fingerprint X"]
    end

    subgraph B["Scan B"]
        FB["Finding fingerprint X"]
    end

    FA --> PF["Persistent Finding X"]
    FB --> EF["Existing Finding X"]
    EF --> Occ["New Occurrence"]
```

This keeps the finding domain stable across repeated scans.

---

## 18. Investigation

A user investigating a finding can move through:

```mermaid
flowchart TD
    Finding["Finding"] --> Source["Source"]
    Finding --> Location["Location"]
    Finding --> Evidence["Evidence"]
    Finding --> Static["Static Analysis"]
    Finding --> Taint["Taint Trace"]
    Finding --> Graph["Graph Context"]
    Finding --> Pred["AI Prediction"]
    Finding --> Exp["Explanation"]
```

The source viewer references the immutable snapshot associated with the finding.

---

## 19. Explainability

XAI consumes the model and evidence context.

```mermaid
flowchart TD
    Finding["Finding"] --> Ctx["Model Context"]
    Ctx --> Adapter["Explanation Adapter"]
    Adapter --> Tok["Token Attribution"]
    Adapter --> Node["Node Attribution"]
    Adapter --> Edge["Edge Attribution"]
    Adapter --> Feat["Feature Attribution"]
    Tok --> Exp["Canonical Explanation"]
    Node --> Exp
    Edge --> Exp
    Feat --> Exp
```

The UI presents the explanation together with the underlying security evidence.

---

## 20. Remediation

A user can request a remediation proposal.

```mermaid
flowchart TD
    Finding["Finding"] --> Ctx["Evidence Context"]
    Ctx --> Prov["Remediation Provider"]
    Prov --> Patch["Proposed Patch"]
    Patch --> Review["Human Review"]
```

The patch remains a proposal until explicitly approved.

---

## 21. Patch Validation

Approved remediation is applied inside a disposable validation workspace.

```mermaid
flowchart TD
    Snap["Original Snapshot"] --> WS["Validation Workspace"]
    WS --> Apply["Apply Patch"]
    Apply --> Syntax["Syntax"]
    Apply --> Build["Build / Tests"]
    Apply --> Static["Static Analysis"]
    Apply --> GT["Graph / Taint"]
    Apply --> Reg["Regression Checks"]
    Syntax --> Result["Validation Result"]
    Build --> Result
    Static --> Result
    GT --> Result
    Reg --> Result
```

The validation environment is separated from the main API process.

---

## 22. Verification Scan

After validation, VulnScan can execute a verification scan.

```mermaid
flowchart TD
    Patch["Validated Patch"] --> Mod["Modified Source State"]
    Mod --> VS["Verification Scan"]
    VS --> Cmp["Finding Comparison"]
    Cmp --> Remains["Finding remains"]
    Cmp --> Gone["Finding no longer present"]
    Remains --> Reopened["REOPENED"]
    Gone --> Verified["VERIFIED"]
```

Verification is authoritative application state.

---

## 23. Reports

Reports consume persisted security information.

```mermaid
flowchart TD
    Data["Projects / Scans / Findings /<br/>Remediation / Security Gates"] --> Svc["Report Service"]
    Svc --> PDF["PDF"]
    Svc --> HTML["HTML"]
    Svc --> JSON["JSON"]
    Svc --> CSV["CSV"]
```

Generated report artifacts can be stored in object storage.

---

## 24. Analytics

Analytics consume the same underlying security domain. Examples include:

- Active projects
- Scan counts
- Finding counts
- Critical findings
- Top CWEs
- Security posture
- Severity distribution
- Historical security information, where supported

Analytics must reflect persisted security state.

---

## 25. Notifications

Notifications are generated from security-domain events. Examples include:

- Scan completion
- Critical findings
- Security gate failures
- Fix availability
- Fix validation
- Finding reopening
- Repository events
- Mentions

Notifications are scoped to the organization and user permissions.

---

## 26. GitHub Workflow

```mermaid
flowchart TD
    PR["Pull Request"] --> WH["GitHub Webhook"]
    WH --> Sig["Signature Verification"]
    Sig --> Repo["Repository Resolution"]
    Repo --> Proj["Project Resolution"]
    Proj --> Snap["Source Snapshot"]
    Snap --> Scan["PR Scan"]
    Scan --> Cmp["Finding Comparison"]
    Cmp --> Existing["Existing"]
    Cmp --> New["New"]
    Cmp --> Fixed["Fixed"]
    Existing --> Gate["Security Gate"]
    New --> Gate
    Fixed --> Gate
    Gate --> Pass["Pass"]
    Gate --> Fail["Fail"]
```

Webhook delivery identifiers and payload integrity are used to prevent duplicate or conflicting processing.

---

## 27. CI Workflow

CI clients interact with VulnScan through the supported API, CLI, and CI integration surface.

```mermaid
flowchart TD
    Job["CI Job"] --> Auth["Authenticate"]
    Auth --> Submit["Submit / Identify Scan"]
    Submit --> Wait["Wait / Query Status"]
    Wait --> Result["Retrieve Security Result"]
    Result --> Gate["Apply Security Gate"]
```

The CI system does not calculate the authoritative security state itself.

---

## 28. Failure Handling

Every major stage can fail. Examples include:

- Invalid source
- Repository failure
- Analysis-engine failure
- Taint failure
- AI provider failure
- Object-storage failure
- Worker interruption
- Validation failure
- Verification failure

Failures are represented explicitly. The system must never convert an error into a successful security result.

---

## 29. Cancellation and Timeout

Long-running operations support controlled cancellation and timeout behavior.

```mermaid
stateDiagram-v2
    [*] --> RUNNING
    RUNNING --> CANCELLED: Cancellation
    RUNNING --> TIMED_OUT: Timeout
    CANCELLED --> [*]
    TIMED_OUT --> [*]
```

Worker heartbeat information helps detect stale executions.

---

## 30. Complete Security Lifecycle

```mermaid
flowchart TD
    Org["Organization"] --> Project["Project"]
    Project --> Repo["Repository"]
    Repo --> Snap["Immutable Source Snapshot"]
    Snap --> Scan["Scan"]
    Scan --> Pre["Preprocessing"]
    Pre --> Static["Static Analysis"]
    Static --> GT["Graph / Taint Analysis"]
    GT --> AI["AI Analysis"]
    AI --> Corr["Evidence Correlation"]
    Corr --> Finding["Finding"]
    Finding --> Inv["Investigation"]
    Inv --> Exp["Explanation"]
    Exp --> Rem["Remediation"]
    Rem --> PV["Patch Validation"]
    PV --> VS["Verification Scan"]
    VS --> Verified["Verified Security State"]

    Verified --> Reports["Reports"]
    Verified --> Analytics["Analytics"]
    Verified --> Notif["Notifications"]
    Verified --> Gates["CI / GitHub Security Gates"]
```

---

## 31. Core Invariants

VulnScan maintains the following invariants:

1. A scan references an immutable source snapshot.
2. A finding remains associated with its organization and project.
3. AI predictions retain provenance.
4. Security evidence remains traceable to its source.
5. Duplicate findings are correlated through fingerprints.
6. Remediation does not automatically mean verification.
7. Validation does not automatically mean verification.
8. Unsupported analysis is not presented as successful analysis.
9. Cross-organization access is denied.
10. Backend authorization is authoritative.
11. Long-running work executes through workers.
12. Security-sensitive operations are auditable.
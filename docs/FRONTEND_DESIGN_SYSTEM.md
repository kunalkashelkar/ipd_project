# VulnScan Frontend Design System & Interaction Architecture

## 1. Vision & Core Philosophy

**VulnScan** is a professional, developer-focused application security workstation designed for security engineers, DevSecOps practitioners, and software developers. 

The design philosophy is:
> **Security Operations Workstation + Developer Tooling + High-End Precision**

### Core Principles
1. **Dense, Never Cramped**: Security analysis requires viewing code, evidence, AST/CPG graphs, and taint propagation simultaneously. Layouts maximize visible information density through compact tables, split panes, and contextual side drawers.
2. **Calm, Never Boring**: Deep slate/charcoal surfaces (`#090D12`, `#0D1219`, `#131923`) reduce eye fatigue during extended security reviews, accented with controlled, purposeful semantic signals.
3. **Restrained Color Semantics**: Color indicates security state, severity, or active execution—never pure decorative novelty.
4. **Authentic Data Only**: Zero fabricated graphs, mock metrics, or synthetic trendlines. If data does not exist or an analysis engine is not configured, the interface explicitly communicates its state.
5. **No Dead-End Navigation**: Every screen answers: *Where am I? What can I do here? What is the primary next action? How do I recover from an error?*

---

## 2. Brand Identity & Official Logo

- **Product Name**: `VulnScan`
- **Emblem**: Multi-layered shield in vivid gradient amber-orange (`#F97316`) and deep royal violet (`#7C3AED`) surrounded by orbiting cyan (`#06B6D4`) and cobalt blue (`#3B82F6`) gravitational trajectory rings, featuring a bold central **V** emblem.
- **Component**: `<VulnScanLogo variant="full" | "icon" | "compact" | "wordmark" size="xs" | "sm" | "md" | "lg" | "xl" | "2xl" />`
  - `full`: Emblem + wordmark + optional subtitle (default)
  - `compact`: Emblem + wordmark without subtitle
  - `icon`: Emblem only (used in page headers, badges, footers)
  - `wordmark`: Typography only without emblem
- **Location Assets**:
  - `frontend/public/logo.png`
  - `frontend/public/favicon.png`
  - `frontend/src/assets/logo.png`
- **Branding Rules**:
  - Use `VulnScan` canonically in all UI strings, page headers, document metadata, and notifications.
  - Never use "IPD" or generic "AI Platform" as product names.

---

## 3. Design Tokens & Color Semantics

### Surface Hierarchy
| Level | Token | Hex Value | Purpose |
| :--- | :--- | :--- | :--- |
| **Canvas** | `background` | `#090D12` | Root page background |
| **Sidebar / Rail** | `sidebar` | `#0D1219` | Persistent primary navigation rail |
| **Card / Panel** | `card` | `#131923` | High-density data containers, workstation modules |
| **Elevated / Overlay** | `popover` / `elevated` | `#18202D` | Dialogs, menus, tooltips, command palette |
| **Subtle Border** | `border` | `#212C3D` | Structural boundaries and table dividers |
| **Hover Surface** | `hover` | `#1C2636` | Row, card, and interactive control hover state |

### Security Severity Matrix
| Severity | Text / Accent | Background Tint | Border Tint | Dot Hex |
| :--- | :--- | :--- | :--- | :--- |
| **Critical** | `#FB7185` (`rose-400`) | `rgba(244, 63, 94, 0.10)` | `rgba(244, 63, 94, 0.30)` | `#F43F5E` |
| **High** | `#FB923C` (`orange-400`) | `rgba(249, 115, 22, 0.10)` | `rgba(249, 115, 22, 0.30)` | `#F97316` |
| **Medium** | `#FBBF24` (`amber-400`) | `rgba(245, 158, 11, 0.10)` | `rgba(245, 158, 11, 0.30)` | `#F59E0B` |
| **Low** | `#38BDF8` (`sky-400`) | `rgba(14, 165, 233, 0.10)` | `rgba(14, 165, 233, 0.30)` | `#0EA5E9` |
| **Fixed / Verified** | `#34D399` (`emerald-400`)| `rgba(16, 185, 129, 0.10)`| `rgba(16, 185, 129, 0.30)`| `#10B981` |

---

## 4. Typography

### Typefaces
- **Primary Sans**: `Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `sans-serif`
  - Body copy, instructions, UI labels, buttons, navigation items.
- **Display Sans**: `Sora`, `Inter`, `sans-serif`
  - Page titles, primary numbers in security posture scores, modal titles.
- **Monospace**: `JetBrains Mono`, `Fira Code`, `ui-monospace`, `monospace`
  - Finding IDs (`fnd_...`), Scan IDs (`scn_...`), Project public IDs (`prj_...`), Git commit SHAs, file paths, code inspection, and tabular numbers.

### Hierarchy & Sizes
- **Page Title**: `text-2xl font-bold tracking-tight text-foreground`
- **Section Title**: `text-base font-semibold text-foreground`
- **Body Regular**: `text-sm text-foreground`
- **Metadata / Secondary**: `text-xs text-muted-foreground`
- **Micro-Labels & Badges**: `text-[10px] uppercase font-semibold tracking-wider`
- **Tabular Numerals**: Enforced via `.tabular-nums` class for jitter-free score counters.

---

## 5. Layout & Navigation Architecture

### Shell Structure
- **Persistent Sidebar** (`256px` wide):
  - Brand header with `<VulnScanLogo />` and edition subtitle ("Security Intelligence").
  - Semantic section groupings:
    - *Investigation*: Dashboard, Projects, Scans, Findings
    - *Intelligence*: Analytics, Reports
    - *Operations*: Integrations, Team & RBAC, Documentation
  - Selected-state vertical rail indicator, subtle hover state (`#1C2636`).
  - Active workspace and user identity footer with quick logout.
- **TopBar**:
  - Contextual workspace title and quick breadcrumbs.
  - Global Command Palette trigger button (`⌘K` / `Ctrl+K`).
  - Live notification unread counter indicator.
- **Command Palette** (`<CommandPalette />`):
  - Hotkey: `Cmd/Ctrl + K`.
  - Accessible dialog powered by keyboard navigation (`ArrowUp`, `ArrowDown`, `Enter`, `Escape`).
  - Instant navigation across all main routes, operational workflows, and active projects fetched directly from `projectService.listProjects()`.

---

## 6. Component Guidelines

### Tables & Workstation Data Grids
- **Header**: Sticky `uppercase text-[11px] font-semibold text-muted-foreground bg-muted/30 border-y border-border`.
- **Row**: `hover:bg-hover transition-colors`, with interactive rows wrapped in clickable handlers.
- **Identifiers**: Monospace pills with subtle border (`font-mono text-xs px-2 py-0.5 rounded bg-muted/60 border border-border/40`).
- **Contextual Actions**: Clear, high-contrast actions (`Open`, `Scan`, `Investigate`) aligned to the right.

### Badges & Status Indicators
- **Severity Badges**: Pair a 6px colored dot with uppercase text (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- **State Badges**: Use semantic colors:
  - `safe`: Verified, Fixed, Ready, Active
  - `warning`: In Progress, Under Review, Queued
  - `destructive`: Failed, Open, Critical
  - `outline`: Neutral metadata, CWE IDs, hashes

### Workstation Cards & Panels
- Border: `border border-border/60`.
- Background: `bg-card/70` with subtle elevation.
- Radii: Moderate rounded geometry (`rounded-lg` / `rounded-md`), avoiding oversized bubbly pill radii.

---

## 7. The 9-Stage Scan Pipeline & Visualization

The canonical technical scan workflow:
1. **Created**: Scan entity recorded and bound to immutable source snapshot.
2. **Queued**: Enqueued in Celery worker task backlog.
3. **Preparing**: Isolating containerized execution boundary.
4. **Checkout**: Retrieving cryptographic snapshot tarball from object storage.
5. **Preprocessing**: File discovery, manifest check, encoding validation.
6. **Static Analysis**: AST, CFG, and Call Graph generation.
7. **Graph Processing**: Canonical graph generation and checksumming.
8. **AI Analysis**: Deep learning classification and model inference.
9. **Post-Processing**: Taint flow propagation, sink discovery, and attack path extraction.
10. **Completed**: All canonical artifacts, taint evidence, and findings persisted.

---

## 8. Flagship Screen: Scan Results & Vulnerability Workspace

- **Three-Pane Investigation Architecture**:
  - **Left Pane (Finding Triage List)**: Severity markers, finding titles, CWE tags, file locations, and status filters.
  - **Center Pane (Source & Evidence Viewer)**: High-density monospace source code viewer, active line marker highlighting the vulnerable statement, and surrounding context.
  - **Right Pane (Finding Intelligence)**:
    - *Overview*: CVSS, risk score, confidence rating, fingerprint.
    - *Taint Flow*: Multi-hop attack path from source parameter to execution sink.
    - *Canonical Graphs*: AST, CFG, CPG, and Call Graph metadata.
    - *AI Explanation*: Evidence-aware explanation with attribution tokens/lines.
    - *Remediation Sandbox*: Patch generation, diff preview, sandbox validation tests, and verification status.

---

## 9. Accessibility & Motion

- **Keyboard Navigation**: Fully accessible Command Palette (`⌘K`), focus rings with visible contrast (`focus:ring-1 focus:ring-primary`), semantic HTML buttons and links.
- **Reduced Motion**: Respects `prefers-reduced-motion: reduce`. Motion is reserved strictly for state communication (pipeline progression, loading states, drawer transitions).
- **Screen Reader Support**: Semantic `role="dialog"`, `aria-label`, and text equivalents for all icons.

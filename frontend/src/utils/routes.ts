// ============================================================
// Centralized Canonical Route Builders
// ============================================================
// Single source of truth for generating URLs across the application.
// Always prioritizes opaque public identifiers (prj_..., scn_..., snp_..., fnd_...)
// over internal UUIDs for canonical user-facing navigation.
// ============================================================

export type Identifiable = {
  id?: string;
  public_id?: string | null;
  [key: string]: any;
};

export const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const PUBLIC_ID_REGEX = /^(prj|scn|snp|rpt|fnd)_[a-z0-9]{12}$/i;

export function isUuid(val: string | null | undefined): boolean {
  if (!val) return false;
  return UUID_REGEX.test(val.trim());
}

export function isPublicId(val: string | null | undefined): boolean {
  if (!val) return false;
  return PUBLIC_ID_REGEX.test(val.trim());
}

/**
 * Extracts the canonical public identifier from an entity or ID string.
 * Always prefers public_id over internal UUID.
 */
export function toProjectSlug(project: string | Identifiable | null | undefined): string {
  if (!project) return '';
  if (typeof project === 'string') return project.trim();
  return project.public_id?.trim() || project.id?.trim() || '';
}

export function toSnapshotSlug(snapshot: string | Identifiable | null | undefined): string {
  if (!snapshot) return '';
  if (typeof snapshot === 'string') return snapshot.trim();
  return snapshot.public_id?.trim() || snapshot.id?.trim() || '';
}

export function toScanSlug(scan: string | Identifiable | null | undefined): string {
  if (!scan) return '';
  if (typeof scan === 'string') return scan.trim();
  return scan.public_id?.trim() || scan.id?.trim() || '';
}

export function toFindingSlug(finding: string | Identifiable | null | undefined): string {
  if (!finding) return '';
  if (typeof finding === 'string') return finding.trim();
  return finding.public_id?.trim() || finding.id?.trim() || '';
}

// ── Canonical URL Builders ───────────────────────────────────

export function getProjectUrl(project: string | Identifiable | null | undefined): string {
  const slug = toProjectSlug(project);
  return slug ? `/projects/${slug}` : '/projects';
}

export function getConnectRepoUrl(project: string | Identifiable | null | undefined): string {
  const slug = toProjectSlug(project);
  return slug ? `/projects/${slug}/repository` : '/projects';
}

export function getSnapshotUrl(
  project: string | Identifiable | null | undefined,
  snapshot: string | Identifiable | null | undefined
): string {
  const pSlug = toProjectSlug(project);
  const sSlug = toSnapshotSlug(snapshot);
  if (!pSlug || !sSlug) return getProjectUrl(project);
  return `/projects/${pSlug}/snapshots/${sSlug}`;
}

export function getScanConfigUrl(project: string | Identifiable | null | undefined): string {
  const slug = toProjectSlug(project);
  return slug ? `/projects/${slug}/scan-config` : '/projects';
}

export function getScanProgressUrl(
  project: string | Identifiable | null | undefined,
  scan?: string | Identifiable | null | undefined
): string {
  const pSlug = toProjectSlug(project);
  const sSlug = scan ? toScanSlug(scan) : '';
  if (!pSlug) return '/scans';
  return sSlug ? `/projects/${pSlug}/scan-progress/${sSlug}` : `/projects/${pSlug}/scan-progress`;
}

export function getScanUrl(
  project: string | Identifiable | null | undefined,
  scan: string | Identifiable | null | undefined
): string {
  const pSlug = toProjectSlug(project);
  const sSlug = toScanSlug(scan);
  if (!pSlug || !sSlug) return getProjectUrl(project);
  return `/projects/${pSlug}/scans/${sSlug}`;
}

export function getResultsUrl(
  project: string | Identifiable | null | undefined,
  scan?: string | Identifiable | null | undefined,
  finding?: string | Identifiable | null | undefined
): string {
  const pSlug = toProjectSlug(project);
  const sSlug = scan ? toScanSlug(scan) : '';
  const fSlug = finding ? toFindingSlug(finding) : '';

  const params = new URLSearchParams();
  if (fSlug) {
    params.set('finding', fSlug);
  }
  const queryString = params.toString() ? `?${params.toString()}` : '';

  if (pSlug && sSlug) {
    return `/projects/${pSlug}/scans/${sSlug}/results${queryString}`;
  }
  if (pSlug) {
    return `/projects/${pSlug}/results${queryString}`;
  }
  return '/scans';
}

export function getProjectScansUrl(project: string | Identifiable | null | undefined): string {
  const slug = toProjectSlug(project);
  return slug ? `/projects/${slug}/scans` : '/scans';
}

export function getProjectFindingsUrl(project: string | Identifiable | null | undefined): string {
  const slug = toProjectSlug(project);
  return slug ? `/projects/${slug}/findings` : '/findings';
}

export function getProjectReportsUrl(project: string | Identifiable | null | undefined): string {
  const slug = toProjectSlug(project);
  return slug ? `/projects/${slug}/reports` : '/reports';
}

export function getProjectSettingsUrl(project: string | Identifiable | null | undefined): string {
  const slug = toProjectSlug(project);
  return slug ? `/projects/${slug}/settings` : '/projects';
}

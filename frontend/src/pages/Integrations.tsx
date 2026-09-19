import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Github,
  Shield,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sliders,
  Terminal,
  Save,
  Loader2,
  ExternalLink,
  Code2,
  Plus,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { projectService } from '../services/projectService';
import { securityGateService } from '../services/securityGateService';
import apiClient from '../services/api';
import { Project, PRSecurityResult, SecurityGatePolicy } from '../types';
import toast from 'react-hot-toast';

export default function Integrations() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [isLoadingProjects, setIsLoadingProjects] = useState<boolean>(true);

  // GitHub Integration Status
  const [githubStatus, setGithubStatus] = useState<{
    app_status: string;
    webhook_status: string;
  }>({
    app_status: 'Not configured',
    webhook_status: 'Active',
  });

  // Policy State
  const [policy, setPolicy] = useState<SecurityGatePolicy | null>(null);
  const [isLoadingPolicy, setIsLoadingPolicy] = useState<boolean>(false);
  const [isSavingPolicy, setIsSavingPolicy] = useState<boolean>(false);

  // PR Results State
  const [prResults, setPrResults] = useState<PRSecurityResult[]>([]);
  const [isLoadingPRs, setIsLoadingPRs] = useState<boolean>(false);

  // 1. Fetch Projects & GitHub Status
  useEffect(() => {
    setIsLoadingProjects(true);
    projectService
      .listProjects({ page_size: 100 })
      .then((res) => {
        const items = res.items || [];
        setProjects(items);
        if (items.length > 0) {
          setSelectedProjectId(items[0].public_id || items[0].id);
        }
      })
      .catch(() => {})
      .finally(() => setIsLoadingProjects(false));

    apiClient
      .get('/integrations/github/status')
      .then((res) => {
        if (res.data?.data) {
          setGithubStatus({
            app_status: res.data.data.app_status || 'Not configured',
            webhook_status: res.data.data.webhook_status || 'Active',
          });
        }
      })
      .catch(() => {});
  }, []);

  // 2. Fetch Policy and PR Results for Selected Project
  useEffect(() => {
    if (!selectedProjectId) return;

    setIsLoadingPolicy(true);
    securityGateService
      .getGatePolicy(selectedProjectId)
      .then((p) => setPolicy(p))
      .catch(() => setPolicy(null))
      .finally(() => setIsLoadingPolicy(false));

    setIsLoadingPRs(true);
    securityGateService
      .getPRSecurityResults(selectedProjectId)
      .then((results) => setPrResults(results || []))
      .catch(() => setPrResults([]))
      .finally(() => setIsLoadingPRs(false));
  }, [selectedProjectId]);

  // 3. Save Policy
  const handleSavePolicy = async () => {
    if (!selectedProjectId || !policy) return;
    setIsSavingPolicy(true);
    try {
      const updated = await securityGateService.updateGatePolicy(selectedProjectId, {
        block_new_critical: policy.block_new_critical,
        block_new_high: policy.block_new_high,
        block_secrets: policy.block_secrets,
        cvss_threshold: policy.cvss_threshold,
      });
      setPolicy(updated);
      toast.success('Security gate policy updated and audited');
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to update security gate policy');
    } finally {
      setIsSavingPolicy(false);
    }
  };

  const currentProject = projects.find((p) => (p.public_id || p.id) === selectedProjectId);

  // Zero Projects State
  if (!isLoadingProjects && projects.length === 0) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto pb-12 pt-8">
        <div>
          <h1 className="text-2xl font-bold font-display tracking-tight text-foreground">
            Integrations & Security Gates
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            GitHub Pull Request security gates, webhook verification, and CI/CD pipelines.
          </p>
        </div>

        <Card className="border-border/80 p-8 text-center">
          <Shield className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
          <h2 className="text-base font-semibold text-foreground">No projects yet</h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
            Security gates and pull request analysis are configured per project. Create your first project to configure gate policies and CI/CD automation.
          </p>
          <div className="mt-4">
            <Link to="/projects">
              <Button size="sm" className="gap-1.5 text-xs">
                <Plus className="w-3.5 h-3.5" /> Create Project
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display tracking-tight text-foreground">
            Integrations & Security Gates
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            GitHub Pull Request security gates, webhook verification, and CI/CD pipelines.
          </p>
        </div>

        {/* Project Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-muted-foreground whitespace-nowrap">Project Scope:</label>
          <select
            className="h-8 rounded-md border border-input bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.public_id || p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* GitHub App & Webhook Verification Banner */}
      <Card className="border-border/80 bg-muted/10">
        <CardContent className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-lg bg-foreground/10 flex items-center justify-center shrink-0">
              <Github className="w-5 h-5 text-foreground" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold text-foreground">GitHub Integration</h3>
                <Badge
                  variant="outline"
                  className={
                    githubStatus.app_status === 'Configured'
                      ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px]'
                      : 'bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px]'
                  }
                >
                  GitHub App: {githubStatus.app_status}
                </Badge>
                <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px]">
                  HMAC Verified Webhooks
                </Badge>
                <Badge variant="outline" className="bg-sky-500/10 text-sky-500 border-sky-500/20 text-[10px]">
                  Replay Protected
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Inbound webhooks at <code className="bg-muted px-1 py-0.5 rounded font-mono text-[11px]">/api/v1/integrations/github/webhook</code> trigger automated baseline comparison and gate evaluation on every pull request.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Security Gate Policy Configuration */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="border-border/80">
            <CardHeader className="pb-3 border-b border-border/40">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-primary" /> Project Security Gate
                </CardTitle>
                <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/20">
                  {currentProject?.name || 'Selected Project'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              {isLoadingPolicy ? (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-primary mb-2" />
                  Loading gate policy...
                </div>
              ) : policy ? (
                <>
                  <div className="space-y-3 text-xs">
                    {/* Block New Critical */}
                    <div className="flex items-center justify-between p-2.5 bg-muted/20 rounded border border-border/40">
                      <div>
                        <p className="font-semibold text-foreground">Block New Critical</p>
                        <p className="text-[11px] text-muted-foreground">Fails gate if new Critical &gt; 0</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={policy.block_new_critical}
                        onChange={(e) =>
                          setPolicy({ ...policy, block_new_critical: e.target.checked })
                        }
                        className="w-4 h-4 rounded text-primary focus:ring-primary"
                      />
                    </div>

                    {/* Block New High */}
                    <div className="flex items-center justify-between p-2.5 bg-muted/20 rounded border border-border/40">
                      <div>
                        <p className="font-semibold text-foreground">Block New High</p>
                        <p className="text-[11px] text-muted-foreground">Fails gate if new High &gt; 0</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={policy.block_new_high}
                        onChange={(e) =>
                          setPolicy({ ...policy, block_new_high: e.target.checked })
                        }
                        className="w-4 h-4 rounded text-primary focus:ring-primary"
                      />
                    </div>

                    {/* Block Secrets */}
                    <div className="flex items-center justify-between p-2.5 bg-muted/20 rounded border border-border/40">
                      <div>
                        <p className="font-semibold text-foreground">Block Hardcoded Secrets</p>
                        <p className="text-[11px] text-muted-foreground">Deterministic secret detection</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={policy.block_secrets}
                        onChange={(e) =>
                          setPolicy({ ...policy, block_secrets: e.target.checked })
                        }
                        className="w-4 h-4 rounded text-primary focus:ring-primary"
                      />
                    </div>

                    {/* CVSS Threshold */}
                    <div className="p-2.5 bg-muted/20 rounded border border-border/40">
                      <div className="flex justify-between items-center mb-1">
                        <p className="font-semibold text-foreground">CVSS Score Threshold</p>
                        <span className="font-mono text-primary font-bold">
                          {policy.cvss_threshold ?? 'Disabled'}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="10"
                        step="0.5"
                        value={policy.cvss_threshold ?? 0}
                        onChange={(e) => {
                          const val = parseFloat(e.target.value);
                          setPolicy({ ...policy, cvss_threshold: val > 0 ? val : null });
                        }}
                        className="w-full accent-primary mt-1"
                      />
                      <p className="text-[10px] text-muted-foreground mt-1">
                        Fails if any new finding exceeds this CVSS score
                      </p>
                    </div>
                  </div>

                  <Button
                    onClick={handleSavePolicy}
                    disabled={isSavingPolicy}
                    className="w-full gap-1.5 text-xs font-medium h-8"
                  >
                    {isSavingPolicy ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Save className="w-3.5 h-3.5" />
                    )}
                    Save Gate Policy
                  </Button>
                </>
              ) : (
                <div className="text-xs text-muted-foreground text-center py-4">
                  Select a project to configure its gate policy
                </div>
              )}
            </CardContent>
          </Card>

          {/* CI/CD & CLI Quick Reference */}
          <Card className="border-border/80">
            <CardHeader className="pb-3 border-b border-border/40">
              <CardTitle className="text-xs font-semibold flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-primary" /> CI/CD Automation
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-3 space-y-2 text-xs">
              <p className="text-muted-foreground text-[11px]">
                Run automated scans from any pipeline using the lightweight CLI or GitHub Action:
              </p>
              <div className="bg-muted p-2 rounded font-mono text-[11px] text-foreground/90 overflow-x-auto">
                python -m cli.security_cli scan --project {currentProject?.public_id || selectedProjectId || 'prj_...'}
              </div>
              <p className="text-[10px] text-muted-foreground">
                Exits 0 on gate PASS, 1 on gate FAIL, and 2 on system error.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* PR Security Results Table */}
        <div className="lg:col-span-2">
          <Card className="border-border/80">
            <CardHeader className="pb-3 border-b border-border/40">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary" /> Recent Pull Request Security Results
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {isLoadingPRs ? (
                <div className="py-16 text-center text-xs text-muted-foreground">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-primary mb-2" />
                  Loading PR security results...
                </div>
              ) : prResults.length === 0 ? (
                <div className="py-16 text-center px-4">
                  <Shield className="w-8 h-8 text-muted-foreground/40 mx-auto mb-2" />
                  <h3 className="text-xs font-semibold text-foreground">No PR scans recorded</h3>
                  <p className="text-[11px] text-muted-foreground mt-1 max-w-sm mx-auto">
                    When a pull request is opened or updated on GitHub, its commit snapshot will be analyzed and compared against your base branch.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-border/60 bg-muted/30 text-muted-foreground font-medium">
                        <th className="py-2.5 px-4">PR #</th>
                        <th className="py-2.5 px-4">Branch / Commit</th>
                        <th className="py-2.5 px-4">Gate Result</th>
                        <th className="py-2.5 px-4">New</th>
                        <th className="py-2.5 px-4">Existing</th>
                        <th className="py-2.5 px-4">Fixed</th>
                        <th className="py-2.5 px-4">Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/30 text-foreground">
                      {prResults.map((pr) => (
                        <tr key={pr.id} className="hover:bg-muted/20 transition-colors">
                          <td className="py-3 px-4 font-semibold text-primary">
                            #{pr.pull_request_number}
                          </td>
                          <td className="py-3 px-4">
                            <span className="font-medium text-foreground block">
                              {pr.pr_branch || 'feature'}
                            </span>
                            <span className="font-mono text-[10px] text-muted-foreground">
                              {pr.pr_head_sha.slice(0, 7)}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            {pr.gate_result === 'PASS' ? (
                              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 text-[10px] gap-1">
                                <CheckCircle2 className="w-3 h-3" /> PASS
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="bg-rose-500/10 text-rose-500 border-rose-500/20 text-[10px] gap-1">
                                <XCircle className="w-3 h-3" /> FAIL
                              </Badge>
                            )}
                          </td>
                          <td className="py-3 px-4 font-semibold text-rose-400">
                            +{pr.new_count}
                          </td>
                          <td className="py-3 px-4 text-muted-foreground">
                            {pr.existing_count}
                          </td>
                          <td className="py-3 px-4 font-semibold text-emerald-400">
                            {pr.fixed_count}
                          </td>
                          <td className="py-3 px-4 text-muted-foreground text-[11px]">
                            {pr.completed_at || pr.created_at
                              ? new Date(pr.completed_at || pr.created_at).toLocaleDateString()
                              : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import {
  User,
  Shield,
  Building,
  Key,
  Mail,
  CheckCircle2,
  Lock,
  Plus,
  Trash2,
  Copy,
  Check,
  AlertTriangle,
  ExternalLink,
  RefreshCw,
  Clock,
} from 'lucide-react';
import { useAuthStore } from '../store';
import { apiKeyService, ApiKeyMetadata } from '../services/apiKeyService';
import { authService } from '../services/authService';
import toast from 'react-hot-toast';

export default function Settings() {
  const { user, activeOrganization, activeMemberRole } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'profile' | 'api-keys' | 'security'>('profile');

  // API Keys state
  const [apiKeys, setApiKeys] = useState<ApiKeyMetadata[]>([]);
  const [isLoadingKeys, setIsLoadingKeys] = useState(false);
  const [isCreateKeyModalOpen, setIsCreateKeyModalOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyExpiryDays, setNewKeyExpiryDays] = useState<number>(30);
  const [isCreatingKey, setIsCreatingKey] = useState(false);
  const [createdKeySecret, setCreatedKeySecret] = useState<string | null>(null);
  const [copiedSecret, setCopiedSecret] = useState(false);

  // Revocation state
  const [keyToRevoke, setKeyToRevoke] = useState<ApiKeyMetadata | null>(null);
  const [isRevoking, setIsRevoking] = useState(false);

  // Security / Password Reset state
  const [isRequestingReset, setIsRequestingReset] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [devResetUrl, setDevResetUrl] = useState<string | null>(null);

  const loadApiKeys = async () => {
    if (!activeOrganization?.id) return;
    setIsLoadingKeys(true);
    try {
      const keys = await apiKeyService.listApiKeys(activeOrganization.id);
      setApiKeys(keys);
    } catch {
      // Handled by interceptor
    } finally {
      setIsLoadingKeys(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'api-keys') {
      loadApiKeys();
    }
  }, [activeTab, activeOrganization?.id]);

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeOrganization?.id || !newKeyName.trim()) return;

    setIsCreatingKey(true);
    try {
      const created = await apiKeyService.createApiKey(
        activeOrganization.id,
        newKeyName.trim(),
        newKeyExpiryDays || undefined
      );
      setCreatedKeySecret(created.api_key);
      toast.success('API key generated successfully!');
      loadApiKeys();
    } catch (err: any) {
      const msg = err?.response?.data?.message || 'Failed to create API key.';
      toast.error(msg);
    } finally {
      setIsCreatingKey(false);
    }
  };

  const handleRevokeKey = async () => {
    if (!activeOrganization?.id || !keyToRevoke) return;

    setIsRevoking(true);
    try {
      await apiKeyService.revokeApiKey(activeOrganization.id, keyToRevoke.id);
      toast.success(`Revoked API key "${keyToRevoke.name}".`);
      setKeyToRevoke(null);
      loadApiKeys();
    } catch (err: any) {
      const msg = err?.response?.data?.message || 'Failed to revoke API key.';
      toast.error(msg);
    } finally {
      setIsRevoking(false);
    }
  };

  const handleCopySecret = async (secret: string) => {
    try {
      await navigator.clipboard.writeText(secret);
      setCopiedSecret(true);
      toast.success('API key secret copied to clipboard!');
      setTimeout(() => setCopiedSecret(false), 2000);
    } catch {
      toast.error('Could not copy to clipboard.');
    }
  };

  const handlePasswordResetRequest = async () => {
    if (!user?.email) return;
    setIsRequestingReset(true);
    setResetMessage(null);
    setDevResetUrl(null);

    try {
      const res = await authService.requestPasswordReset(user.email);
      setResetMessage('A password reset request has been processed for your account.');
      if (res?.reset_url) {
        setDevResetUrl(res.reset_url);
      } else if (res?.dev_token) {
        setDevResetUrl(`/reset-password?token=${res.dev_token}`);
      }
      toast.success('Password reset initiated.');
    } catch (err: any) {
      const msg = err?.response?.data?.message || 'Password reset request completed.';
      setResetMessage(msg);
    } finally {
      setIsRequestingReset(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage your account credentials, workspace API keys, and platform security.</p>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Settings Navigation */}
        <div className="w-full md:w-64 space-y-1">
          {[
            { id: 'profile', label: 'Profile Information', icon: User },
            { id: 'api-keys', label: 'Organization API Keys', icon: Key },
            { id: 'security', label: 'Security & Password', icon: Lock },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id as any)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
                activeTab === item.id
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </button>
          ))}
        </div>

        {/* Settings Content Area */}
        <div className="flex-1 space-y-6">
          {/* TAB 1: Profile Information */}
          {activeTab === 'profile' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="w-5 h-5 text-primary" /> Authenticated Profile
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Full Name</label>
                  <input
                    type="text"
                    readOnly
                    value={user?.name || ''}
                    className="w-full bg-muted/50 border border-border rounded-md px-3 py-2 text-sm text-foreground focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Email Address</label>
                  <div className="relative">
                    <input
                      type="email"
                      readOnly
                      value={user?.email || ''}
                      className="w-full bg-muted/50 border border-border rounded-md px-3 py-2 text-sm text-foreground focus:outline-none font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  <div className="p-3 rounded-lg border border-border bg-card space-y-1">
                    <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                      <Building className="w-3.5 h-3.5 text-primary" /> Active Workspace
                    </div>
                    <div className="text-sm font-semibold text-foreground">
                      {activeOrganization?.name || 'No active workspace'}
                    </div>
                  </div>

                  <div className="p-3 rounded-lg border border-border bg-card space-y-1">
                    <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                      <Shield className="w-3.5 h-3.5 text-primary" /> Identity Role
                    </div>
                    <div className="text-sm font-semibold text-foreground capitalize">
                      {activeMemberRole
                        ? activeMemberRole.replace('_', ' ')
                        : activeOrganization?.current_user_role
                        ? activeOrganization.current_user_role.replace('_', ' ')
                        : (user?.role ? user.role.replace('_', ' ') : 'Member')}
                    </div>
                  </div>
                </div>

                <div className="p-3.5 rounded-lg bg-muted/30 border border-border flex items-start gap-2.5 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                  <span>
                    Self-service profile modification is currently disabled to ensure audit trail immutability across organizations. Contact your workspace administrator or owner to request identity changes.
                  </span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* TAB 2: Organization API Keys */}
          {activeTab === 'api-keys' && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Key className="w-5 h-5 text-primary" /> Workspace API Keys
                  </CardTitle>
                  <p className="text-xs text-muted-foreground mt-1">
                    Keys provide programmatic API access to {activeOrganization?.name || 'this workspace'}.
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => {
                    setCreatedKeySecret(null);
                    setNewKeyName('');
                    setNewKeyExpiryDays(30);
                    setIsCreateKeyModalOpen(true);
                  }}
                  className="gap-1.5"
                >
                  <Plus className="w-4 h-4" /> Create Key
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                {isLoadingKeys ? (
                  <div className="py-12 flex items-center justify-center">
                    <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
                  </div>
                ) : apiKeys.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground border border-dashed border-border rounded-xl">
                    <Key className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p className="font-medium text-foreground">No API keys created</p>
                    <p className="text-xs mt-1">Create an API key to integrate external CI/CD pipelines.</p>
                  </div>
                ) : (
                  <div className="divide-y divide-border border border-border rounded-lg overflow-hidden">
                    {apiKeys.map((key) => (
                      <div key={key.id} className="p-4 flex items-center justify-between bg-card hover:bg-muted/10 transition-colors">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm text-foreground">{key.name}</span>
                            <Badge variant={key.revoked ? 'destructive' : 'outline'} className="text-[10px]">
                              {key.revoked ? 'Revoked' : 'Active'}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono">
                            <span>Prefix: {key.key_prefix}••••••••</span>
                            <span>•</span>
                            <span>Created: {new Date(key.created_at).toLocaleDateString()}</span>
                            {key.expires_at && (
                              <>
                                <span>•</span>
                                <span>Expires: {new Date(key.expires_at).toLocaleDateString()}</span>
                              </>
                            )}
                          </div>
                        </div>
                        <div>
                          {!key.revoked && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setKeyToRevoke(key)}
                              className="text-destructive hover:bg-destructive/10 text-xs"
                            >
                              <Trash2 className="w-3.5 h-3.5 mr-1" /> Revoke
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* TAB 3: Security & Password */}
          {activeTab === 'security' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Lock className="w-5 h-5 text-primary" /> Security & Sessions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold text-foreground">Password Recovery & Reset</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Initiate a cryptographically secure password reset. Completing password reset will invalidate all active sessions across all devices for your protection.
                  </p>
                  <Button
                    onClick={handlePasswordResetRequest}
                    disabled={isRequestingReset}
                    variant="outline"
                    className="gap-2 mt-2 text-xs"
                  >
                    {isRequestingReset ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Lock className="w-3.5 h-3.5" />
                    )}
                    Send Password Reset Request
                  </Button>
                </div>

                {resetMessage && (
                  <div className="p-4 rounded-xl bg-primary/10 border border-primary/20 space-y-2">
                    <p className="text-xs text-foreground font-medium flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-primary" /> {resetMessage}
                    </p>
                    {devResetUrl && (
                      <div className="pt-2 border-t border-primary/20">
                        <span className="text-[10px] uppercase font-bold text-primary tracking-wider block mb-1">
                          Development Reset Link:
                        </span>
                        <a
                          href={devResetUrl}
                          className="text-xs font-mono text-primary underline flex items-center gap-1 hover:text-cyan-400"
                        >
                          {devResetUrl} <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    )}
                  </div>
                )}

                <div className="border-t border-border pt-4 space-y-2">
                  <h4 className="text-sm font-semibold text-foreground">Session Invalidation Policy</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    User sessions are backed by server-side PostgreSQL records and Redis rotation caches. Signing out or resetting your password immediately revokes active refresh tokens and forces re-authentication.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Modal: Create API Key */}
      {isCreateKeyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <Card className="max-w-md w-full border-border shadow-2xl">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Key className="w-5 h-5 text-primary" /> Create API Key
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {createdKeySecret ? (
                <div className="space-y-4">
                  <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>
                      Copy this secret key now. For your security, this plaintext secret will never be displayed again.
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground">Generated Key Secret</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        readOnly
                        value={createdKeySecret}
                        className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-xs font-mono text-foreground focus:outline-none"
                      />
                      <Button
                        size="sm"
                        onClick={() => handleCopySecret(createdKeySecret)}
                        className="shrink-0 gap-1"
                      >
                        {copiedSecret ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        {copiedSecret ? 'Copied' : 'Copy'}
                      </Button>
                    </div>
                  </div>
                  <div className="pt-2 flex justify-end">
                    <Button
                      onClick={() => {
                        setIsCreateKeyModalOpen(false);
                        setCreatedKeySecret(null);
                      }}
                    >
                      Done
                    </Button>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleCreateApiKey} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-foreground">Key Name *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. GitHub Actions CI"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-foreground">Expiration</label>
                    <select
                      value={newKeyExpiryDays}
                      onChange={(e) => setNewKeyExpiryDays(Number(e.target.value))}
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:ring-1 focus:ring-primary outline-none"
                    >
                      <option value={30}>30 Days</option>
                      <option value={60}>60 Days</option>
                      <option value={90}>90 Days</option>
                      <option value={365}>1 Year</option>
                      <option value={0}>Never Expire</option>
                    </select>
                  </div>

                  <div className="pt-2 flex justify-end gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setIsCreateKeyModalOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      disabled={isCreatingKey || !newKeyName.trim()}
                    >
                      {isCreatingKey ? 'Generating...' : 'Generate Key'}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Revocation Confirmation Dialog */}
      <ConfirmDialog
        isOpen={Boolean(keyToRevoke)}
        onClose={() => setKeyToRevoke(null)}
        onConfirm={handleRevokeKey}
        title="Revoke API Key"
        message={`Are you sure you want to revoke "${keyToRevoke?.name}"? Any applications or automated scripts using this key will immediately lose access.`}
        confirmText="Revoke Key"
        variant="destructive"
        isLoading={isRevoking}
      />
    </div>
  );
}

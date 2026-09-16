// ============================================================
// Team & RBAC Management Page — Production-Grade SaaS Experience
// ============================================================

import React, { useEffect, useState, useMemo } from 'react';
import {
  Users,
  Shield,
  Plus,
  Mail,
  Trash2,
  ShieldAlert,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  KeyRound,
  ChevronRight,
  X,
  ExternalLink,
  Crown,
  Lock,
} from 'lucide-react';
import {
  PageHeader,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
  Spinner,
} from '../components/ui';
import { useAuthStore } from '../store';
import { teamService } from '../services/teamService';
import { organizationService } from '../services/organizationService';
import { OrganizationMember, OrganizationInvitation, RoleWithPermissions } from '../types';
import toast from 'react-hot-toast';
import { RefreshCw } from 'lucide-react';

// The 5 Predefined System Roles & Descriptions
export const PREDEFINED_ROLES = [
  {
    name: 'owner',
    displayName: 'Owner',
    description: 'Full organization administration and ownership controls.',
    color: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    icon: Crown,
  },
  {
    name: 'admin',
    displayName: 'Admin',
    description: 'Organization and team administration.',
    color: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    icon: Shield,
  },
  {
    name: 'security_analyst',
    displayName: 'Security Analyst',
    description: 'Security and vulnerability-analysis workflows.',
    color: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    icon: ShieldAlert,
  },
  {
    name: 'developer',
    displayName: 'Developer',
    description: 'Development/project workflows permitted by the organization.',
    color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    icon: Users,
  },
  {
    name: 'viewer',
    displayName: 'Viewer',
    description: 'Read-only access.',
    color: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/30',
    icon: Lock,
  },
] as const;

export default function Team() {
  const { user, activeOrganization, setActiveOrganization, setActiveMemberRole, organizations } = useAuthStore();

  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
  const [rolesWithPerms, setRolesWithPerms] = useState<RoleWithPermissions[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<{ message: string; status?: number } | null>(null);

  // Modals state
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'security_analyst' | 'developer' | 'viewer'>('developer');
  const [isInviting, setIsInviting] = useState(false);
  const [inviteResult, setInviteResult] = useState<{ token: string; email: string } | null>(null);
  const [copiedToken, setCopiedToken] = useState(false);

  // Role Change Modal state
  const [roleChangeMember, setRoleChangeMember] = useState<OrganizationMember | null>(null);
  const [selectedNewRole, setSelectedNewRole] = useState<string>('developer');
  const [isUpdatingRole, setIsUpdatingRole] = useState(false);

  // Remove Member Modal state
  const [memberToRemove, setMemberToRemove] = useState<OrganizationMember | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);

  // Permissions Drawer state
  const [viewingRolePerms, setViewingRolePerms] = useState<RoleWithPermissions | null>(null);

  // Active sub-tab: 'members' | 'roles'
  const [activeTab, setActiveTab] = useState<'members' | 'roles'>('members');

  // Compute current user's membership and permissions in this organization
  const currentMember = useMemo(
    () => members.find((m) => m.user_id === user?.id),
    [members, user?.id]
  );
  const currentUserRole = currentMember?.role;

  useEffect(() => {
    if (currentUserRole) {
      setActiveMemberRole(currentUserRole);
    }
  }, [currentUserRole, setActiveMemberRole]);

  const isOwner = currentUserRole === 'owner';
  const isAdmin = currentUserRole === 'admin';
  const canManageTeam = isOwner || isAdmin;

  const fetchTeamData = async () => {
    let orgId = activeOrganization?.id;
    if (!orgId) {
      if (organizations && organizations.length > 0) {
        orgId = organizations[0].id;
        setActiveOrganization(organizations[0]);
      } else {
        try {
          const orgs = await organizationService.listOrganizations();
          if (orgs && orgs.length > 0) {
            orgId = orgs[0].id;
            setActiveOrganization(orgs[0]);
          }
        } catch (err: any) {
          setIsLoading(false);
          setFetchError({
            message: err?.response?.data?.message || err?.message || 'Failed to resolve organization context',
            status: err?.response?.status,
          });
          return;
        }
      }
    }

    if (!orgId) {
      setIsLoading(false);
      setFetchError({
        message: 'No active workspace selected. Please select or create an organization.',
      });
      return;
    }

    setIsLoading(true);
    setFetchError(null);
    try {
      const [membersData, invitationsData, rolesData] = await Promise.all([
        teamService.listMembers(orgId),
        teamService.listInvitations(orgId).catch(() => []),
        teamService.listRoles(orgId).catch(() => []),
      ]);
      setMembers(membersData || []);
      setInvitations(invitationsData || []);
      setRolesWithPerms(rolesData || []);
    } catch (err: any) {
      const status = err?.response?.status;
      const message =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to load workspace members';
      setFetchError({ message, status });
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTeamData();
  }, [activeOrganization?.id]);

  // Handle Invite Submission
  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeOrganization || !inviteEmail.trim()) return;

    setIsInviting(true);
    try {
      const invitation = await teamService.inviteMember(
        activeOrganization.id,
        inviteEmail.trim().toLowerCase(),
        inviteRole
      );
      setInvitations((prev) => [invitation, ...prev]);
      if (invitation.invitation_token) {
        setInviteResult({
          token: invitation.invitation_token,
          email: inviteEmail.trim().toLowerCase(),
        });
      } else {
        setIsInviteModalOpen(false);
        setInviteEmail('');
      }
      toast.success(`Invitation sent to ${inviteEmail}`);
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.response?.data?.detail || 'Failed to send invitation';
      toast.error(msg);
    } finally {
      setIsInviting(false);
    }
  };

  // Handle Role Change Submission
  const handleRoleChangeSubmit = async () => {
    if (!activeOrganization || !roleChangeMember) return;
    setIsUpdatingRole(true);
    try {
      const updated = await teamService.changeMemberRole(
        activeOrganization.id,
        roleChangeMember.user_id,
        selectedNewRole
      );
      setMembers((prev) =>
        prev.map((m) => (m.user_id === roleChangeMember.user_id ? updated : m))
      );
      toast.success(`Role updated to ${selectedNewRole} for ${roleChangeMember.user_name}`);
      setRoleChangeMember(null);
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.response?.data?.detail || 'Failed to change role';
      toast.error(msg);
    } finally {
      setIsUpdatingRole(false);
    }
  };

  // Handle Member Removal Submission
  const handleRemoveMemberSubmit = async () => {
    if (!activeOrganization || !memberToRemove) return;
    setIsRemoving(true);
    try {
      await teamService.removeMember(activeOrganization.id, memberToRemove.user_id);
      setMembers((prev) => prev.filter((m) => m.user_id !== memberToRemove.user_id));
      toast.success(`${memberToRemove.user_name} has been removed from the workspace`);
      setMemberToRemove(null);
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.response?.data?.detail || 'Failed to remove member';
      toast.error(msg);
    } finally {
      setIsRemoving(false);
    }
  };

  const getRoleBadge = (roleName: string) => {
    const roleDef = PREDEFINED_ROLES.find((r) => r.name === roleName);
    return (
      <Badge
        variant="outline"
        className={`capitalize font-medium text-xs px-2.5 py-0.5 border ${
          roleDef ? roleDef.color : 'bg-muted text-muted-foreground'
        }`}
      >
        {roleDef ? roleDef.displayName : roleName.replace('_', ' ')}
      </Badge>
    );
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Users className="w-7 h-7 text-primary" /> Team Management
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage members, role assignments, and organization access for{' '}
            <span className="font-semibold text-foreground">
              {activeOrganization?.name || 'Current Workspace'}
            </span>
          </p>
        </div>

        {canManageTeam && (
          <Button
            onClick={() => {
              setInviteResult(null);
              setInviteEmail('');
              setIsInviteModalOpen(true);
            }}
            className="gap-2 shrink-0 shadow-soft"
          >
            <Plus className="w-4 h-4" /> Invite Member
          </Button>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-border pb-2">
        <button
          onClick={() => setActiveTab('members')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeTab === 'members'
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
          }`}
        >
          Members & Invitations ({members.length})
        </button>
        <button
          onClick={() => setActiveTab('roles')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
            activeTab === 'roles'
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
          }`}
        >
          <Shield className="w-4 h-4" /> Roles & Permissions (5)
        </button>
      </div>

      {activeTab === 'members' ? (
        <div className="space-y-6">
          {/* Active Members Table */}
          <Card className="border-border">
            <CardHeader className="pb-3 border-b border-border/50">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Users className="w-4 h-4 text-primary" /> Organization Members ({members.length})
                </CardTitle>
                <span className="text-xs text-muted-foreground">
                  Roles are enforced server-side via RBAC policies
                </span>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Member</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Joined</TableHead>
                    {canManageTeam && <TableHead className="text-right">Actions</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading ? (
                    <TableRow>
                      <TableCell colSpan={canManageTeam ? 6 : 5} className="py-16 text-center">
                        <div className="flex flex-col items-center justify-center gap-3">
                          <Spinner size="lg" />
                          <p className="text-sm font-medium text-foreground">Loading workspace members...</p>
                          <p className="text-xs text-muted-foreground">Retrieving authorized RBAC identities from server</p>
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : fetchError ? (
                    <TableRow>
                      <TableCell colSpan={canManageTeam ? 6 : 5} className="py-16 text-center">
                        <div className="flex flex-col items-center justify-center gap-3 max-w-md mx-auto">
                          <div className="w-12 h-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center">
                            <AlertCircle className="w-6 h-6" />
                          </div>
                          <div>
                            <h3 className="text-sm font-semibold text-foreground">Failed to load team data</h3>
                            <p className="text-xs text-muted-foreground mt-1">{fetchError.message}</p>
                            {fetchError.status && (
                              <p className="text-[11px] font-mono text-muted-foreground mt-0.5">HTTP Status: {fetchError.status}</p>
                            )}
                          </div>
                          <Button size="sm" variant="outline" onClick={fetchTeamData} className="gap-2 mt-2">
                            <RefreshCw className="w-3.5 h-3.5" /> Retry
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : members.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={canManageTeam ? 6 : 5} className="py-12 text-center text-muted-foreground text-sm">
                        No members found in this workspace.
                      </TableCell>
                    </TableRow>
                  ) : (
                    members.map((member) => {
                      const isCurrentUser = member.user_id === user?.id;
                      const isTargetOwner = member.role === 'owner';
                      return (
                        <TableRow key={member.id} className="hover:bg-muted/40 transition-colors">
                          {/* Member Name + Current User Badge */}
                          <TableCell className="font-medium text-foreground">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs border border-primary/20">
                                {member.user_name ? member.user_name.charAt(0).toUpperCase() : 'U'}
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="font-semibold">{member.user_name}</span>
                                {isCurrentUser && (
                                  <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-primary/20 text-primary uppercase tracking-wider">
                                    You
                                  </span>
                                )}
                              </div>
                            </div>
                          </TableCell>

                          {/* Email */}
                          <TableCell className="text-muted-foreground text-sm font-mono">
                            {member.user_email}
                          </TableCell>

                          {/* Role Badge */}
                          <TableCell>{getRoleBadge(member.role)}</TableCell>

                          {/* Status */}
                          <TableCell>
                            <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Active
                            </span>
                          </TableCell>

                          {/* Joined Date */}
                          <TableCell className="text-xs text-muted-foreground">
                            {new Date(member.joined_at).toLocaleDateString(undefined, {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            })}
                          </TableCell>

                          {/* Role-Aware Actions */}
                          {canManageTeam && (
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                {/* Change Role Button */}
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    setRoleChangeMember(member);
                                    setSelectedNewRole(member.role);
                                  }}
                                  className="text-xs text-muted-foreground hover:text-foreground"
                                  title="Change role"
                                >
                                  Change role
                                </Button>

                                {/* Remove Member Button */}
                                {(!isTargetOwner || members.filter((m) => m.role === 'owner').length > 1) && !isCurrentUser && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setMemberToRemove(member)}
                                    className="text-destructive hover:bg-destructive/10 h-8 w-8 p-0"
                                    title="Remove member"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </Button>
                                )}
                              </div>
                            </TableCell>
                          )}
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Pending Invitations Section */}
          {canManageTeam && invitations.length > 0 && (
            <Card className="border-border">
              <CardHeader className="pb-3 border-b border-border/50">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Mail className="w-4 h-4 text-primary" /> Pending Invitations ({invitations.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Invited Email</TableHead>
                      <TableHead>Assigned Role</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Expires</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {invitations.map((inv) => (
                      <TableRow key={inv.id}>
                        <TableCell className="font-medium text-foreground font-mono text-xs">
                          {inv.invited_email}
                        </TableCell>
                        <TableCell>{getRoleBadge(inv.role_name)}</TableCell>
                        <TableCell>
                          <Badge variant="secondary" className="capitalize text-xs">
                            {inv.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {new Date(inv.expires_at).toLocaleDateString(undefined, {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        /* Roles & Permissions Section */
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-card border border-border flex items-start gap-3">
            <KeyRound className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-foreground">Predefined Organization Roles</h3>
              <p className="text-xs text-muted-foreground">
                To guarantee zero ambiguity and ironclad tenant isolation, our platform implements five immutable system roles. Roles are assigned to members by authorized team administrators.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {PREDEFINED_ROLES.map((roleDef) => {
              const RoleIcon = roleDef.icon;
              const backendRole = rolesWithPerms.find((r) => r.name === roleDef.name);
              const permsCount = backendRole?.permissions?.length ?? 0;

              return (
                <Card key={roleDef.name} className="border-border hover:border-primary/40 transition-colors flex flex-col justify-between">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${roleDef.color}`}>
                          <RoleIcon className="w-4 h-4" />
                        </div>
                        <CardTitle className="text-base font-semibold text-foreground">
                          {roleDef.displayName}
                        </CardTitle>
                      </div>
                      <Badge variant="outline" className="text-[11px] capitalize">
                        {permsCount > 0 ? `${permsCount} perms` : 'Predefined'}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {roleDef.description}
                    </p>
                    <div className="pt-2 border-t border-border/50 flex items-center justify-between">
                      <span className="text-[11px] text-muted-foreground">Authoritative Policy</span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          if (backendRole) {
                            setViewingRolePerms(backendRole);
                          } else {
                            toast.error('Permissions metadata not yet loaded from backend.');
                          }
                        }}
                        className="text-xs gap-1"
                      >
                        View permissions <ChevronRight className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 1. INVITE MEMBER MODAL */}
      {/* ============================================================ */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-xl max-w-md w-full p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <Mail className="w-5 h-5 text-primary" /> Invite Team Member
              </h3>
              <button
                onClick={() => setIsInviteModalOpen(false)}
                className="text-muted-foreground hover:text-foreground rounded-lg p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {inviteResult ? (
              /* Success & Dev Link view */
              <div className="space-y-4">
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-400 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold">Invitation Generated!</div>
                    <div>
                      An invitation token has been created for <span className="font-mono">{inviteResult.email}</span>.
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Acceptance Link</label>
                  <div className="flex items-center gap-2">
                    <input
                      readOnly
                      value={`${window.location.origin}/invitations/accept?token=${inviteResult.token}`}
                      className="w-full text-xs font-mono p-2 rounded bg-muted border border-border text-foreground select-all"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        navigator.clipboard.writeText(
                          `${window.location.origin}/invitations/accept?token=${inviteResult.token}`
                        );
                        setCopiedToken(true);
                        toast.success('Link copied to clipboard!');
                        setTimeout(() => setCopiedToken(false), 2000);
                      }}
                      className="shrink-0"
                    >
                      {copiedToken ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </Button>
                  </div>
                </div>

                <Button
                  className="w-full"
                  onClick={() => {
                    setIsInviteModalOpen(false);
                    setInviteResult(null);
                    setInviteEmail('');
                  }}
                >
                  Done
                </Button>
              </div>
            ) : (
              /* Invitation Form */
              <form onSubmit={handleInviteSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground">Email Address</label>
                  <input
                    type="email"
                    required
                    placeholder="teammate@company.com"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium text-foreground">Assign Role</label>
                  <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                    {PREDEFINED_ROLES.filter((r) => r.name !== 'owner').map((role) => (
                      <label
                        key={role.name}
                        className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                          inviteRole === role.name
                            ? 'bg-primary/5 border-primary'
                            : 'border-border hover:bg-muted/50'
                        }`}
                      >
                        <input
                          type="radio"
                          name="inviteRole"
                          value={role.name}
                          checked={inviteRole === role.name}
                          onChange={() => setInviteRole(role.name as any)}
                          className="mt-0.5"
                        />
                        <div className="space-y-0.5">
                          <div className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                            {role.displayName}
                          </div>
                          <div className="text-[11px] text-muted-foreground leading-snug">
                            {role.description}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                  <p className="text-[11px] text-muted-foreground italic">
                    Note: Owner roles cannot be directly invited. Existing members can be promoted to Owner.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setIsInviteModalOpen(false)}
                    disabled={isInviting}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isInviting || !inviteEmail.trim()}>
                    {isInviting ? (
                      <>
                        <Spinner size="sm" /> Sending...
                      </>
                    ) : (
                      'Send Invitation'
                    )}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 2. CHANGE ROLE MODAL */}
      {/* ============================================================ */}
      {roleChangeMember && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-xl max-w-md w-full p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h3 className="text-lg font-semibold text-foreground">Change Role</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Update permissions for <span className="font-semibold text-foreground">{roleChangeMember.user_name}</span>
                </p>
              </div>
              <button
                onClick={() => setRoleChangeMember(null)}
                className="text-muted-foreground hover:text-foreground rounded-lg p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
              {PREDEFINED_ROLES.map((role) => (
                <label
                  key={role.name}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedNewRole === role.name
                      ? 'bg-primary/5 border-primary ring-1 ring-primary'
                      : 'border-border hover:bg-muted/50'
                  }`}
                >
                  <input
                    type="radio"
                    name="selectedNewRole"
                    value={role.name}
                    checked={selectedNewRole === role.name}
                    onChange={() => setSelectedNewRole(role.name)}
                    className="mt-0.5"
                  />
                  <div className="space-y-0.5">
                    <div className="text-xs font-semibold text-foreground flex items-center gap-2">
                      <span>{role.displayName}</span>
                      {roleChangeMember.role === role.name && (
                        <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                          Current
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-muted-foreground leading-snug">
                      {role.description}
                    </div>
                  </div>
                </label>
              ))}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button
                variant="outline"
                onClick={() => setRoleChangeMember(null)}
                disabled={isUpdatingRole}
              >
                Cancel
              </Button>
              <Button
                onClick={handleRoleChangeSubmit}
                disabled={isUpdatingRole || selectedNewRole === roleChangeMember.role}
              >
                {isUpdatingRole ? (
                  <>
                    <Spinner size="sm" /> Updating...
                  </>
                ) : (
                  'Save Role'
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 3. REMOVE MEMBER CONFIRMATION MODAL */}
      {/* ============================================================ */}
      {memberToRemove && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-card border border-destructive/30 rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-destructive/10 text-destructive flex items-center justify-center shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-foreground">Remove member?</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Confirm membership revocation
                </p>
              </div>
            </div>

            <p className="text-sm text-muted-foreground leading-relaxed">
              Remove <span className="font-semibold text-foreground">{memberToRemove.user_name}</span> from{' '}
              <span className="font-semibold text-foreground">{activeOrganization?.name}</span>? They will lose access to this organization and all project resources.
            </p>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button
                variant="outline"
                onClick={() => setMemberToRemove(null)}
                disabled={isRemoving}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleRemoveMemberSubmit}
                disabled={isRemoving}
                className="gap-2"
              >
                {isRemoving ? (
                  <>
                    <Spinner size="sm" /> Removing...
                  </>
                ) : (
                  'Remove member'
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 4. ROLES & PERMISSIONS DRAWER / MODAL */}
      {/* ============================================================ */}
      {viewingRolePerms && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-2xl max-w-2xl w-full p-6 space-y-5 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-border pb-3 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                  <Shield className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground capitalize">
                    {viewingRolePerms.name.replace('_', ' ')} Permissions
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Authoritative permissions granted to this role in PostgreSQL
                  </p>
                </div>
              </div>
              <button
                onClick={() => setViewingRolePerms(null)}
                className="text-muted-foreground hover:text-foreground rounded-lg p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Permissions list grouped by category */}
            <div className="overflow-y-auto space-y-4 pr-2 flex-1">
              {Object.entries(
                viewingRolePerms.permissions.reduce<Record<string, typeof viewingRolePerms.permissions>>((acc, perm) => {
                  const cat = perm.category || 'general';
                  if (!acc[cat]) acc[cat] = [];
                  acc[cat].push(perm);
                  return acc;
                }, {})
              ).map(([category, perms]) => (
                <div key={category} className="space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1">
                    {category} ({perms.length})
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {perms.map((p) => (
                      <div
                        key={p.id}
                        className="p-2.5 rounded-lg bg-muted/40 border border-border/60 flex items-start gap-2"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <div className="space-y-0.5">
                          <div className="text-xs font-mono font-medium text-foreground">{p.key}</div>
                          <div className="text-[11px] text-muted-foreground leading-tight">
                            {p.description}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-end pt-3 border-t border-border shrink-0">
              <Button variant="outline" onClick={() => setViewingRolePerms(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

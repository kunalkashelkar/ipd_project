// ============================================================
// Accept Invitation Page — Production-Grade Two-Path UX
// Path 1: Existing Account -> Sign in to accept -> Join workspace
// Path 2: New Account -> Create account & join directly (zero extra org)
// ============================================================

import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import {
  Building,
  Mail,
  Shield,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  Lock,
  User as UserIcon,
  LogIn,
  UserPlus,
  RefreshCw,
  LogOut,
  Clock,
  Eye,
  EyeOff,
} from 'lucide-react';
import { Card, CardContent, Button, Spinner, Badge } from '../components/ui';
import { useAuthStore } from '../store';
import { teamService, InvitationPreview } from '../services/teamService';
import { authService } from '../services/authService';
import { organizationService } from '../services/organizationService';
import { PREDEFINED_ROLES } from './Team';
import toast from 'react-hot-toast';

export default function AcceptInvitation() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();

  const {
    user,
    isAuthenticated,
    login,
    logout,
    setActiveOrganization,
    setOrganizations,
  } = useAuthStore();

  const [invitation, setInvitation] = useState<InvitationPreview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorDetails, setErrorDetails] = useState<{
    type: 'invalid' | 'expired' | 'accepted' | 'already_member' | 'general';
    title: string;
    message: string;
  } | null>(null);

  // Path 1 (Existing Account) Action state
  const [isAccepting, setIsAccepting] = useState(false);

  // Path 2 (New Account) Form state
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      setErrorDetails({
        type: 'invalid',
        title: 'Missing Invitation Token',
        message: 'No invitation token was found in the link. Please check your invitation URL.',
      });
      return;
    }

    const loadDetails = async () => {
      setIsLoading(true);
      setErrorDetails(null);
      try {
        const details = await teamService.getInvitationDetails(token);
        setInvitation(details);

        // Check for already accepted or expired or already member
        if (details.status === 'accepted') {
          setErrorDetails({
            type: 'accepted',
            title: 'Invitation Already Accepted',
            message: 'This invitation has already been accepted.',
          });
        } else if (details.already_member) {
          setErrorDetails({
            type: 'already_member',
            title: 'Already a Member',
            message: 'You already belong to this workspace.',
          });
        } else if (details.status === 'expired' || (details.expires_at && new Date(details.expires_at) < new Date())) {
          setErrorDetails({
            type: 'expired',
            title: 'Invitation Expired',
            message: 'This invitation has expired. Ask your organization administrator to send a new invitation.',
          });
        }
      } catch (err: any) {
        const msg =
          err?.response?.data?.message ||
          err?.response?.data?.detail ||
          'This invitation link is invalid or has expired.';

        if (msg.toLowerCase().includes('expired')) {
          setErrorDetails({
            type: 'expired',
            title: 'Invitation Expired',
            message: 'This invitation has expired. Ask your organization administrator to send a new invitation.',
          });
        } else if (msg.toLowerCase().includes('accepted')) {
          setErrorDetails({
            type: 'accepted',
            title: 'Invitation Already Accepted',
            message: 'This invitation has already been accepted.',
          });
        } else {
          setErrorDetails({
            type: 'invalid',
            title: 'Invalid Invitation Link',
            message: msg,
          });
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadDetails();
  }, [token]);

  // PATH 1: Handle Acceptance for Authenticated Existing Account
  const handleAcceptExisting = async () => {
    if (!token) return;
    setIsAccepting(true);
    try {
      await teamService.acceptInvitation(token);
      toast.success('Successfully joined ' + (invitation?.organization_name || 'the workspace') + '!');

      // Reload organizations and switch active organization to the joined workspace
      const userOrgs = await organizationService.listOrganizations();
      setOrganizations(userOrgs);
      const joinedOrg = userOrgs.find((o) => o.id === invitation?.organization_id);
      if (joinedOrg) {
        setActiveOrganization(joinedOrg);
      }
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      toast.error(
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        'Failed to accept invitation.'
      );
    } finally {
      setIsAccepting(false);
    }
  };

  // PATH 2: Handle Direct Account Creation for New Invitee (Zero Extra Org)
  const handleRegisterAndJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !invitation) return;

    if (password.length < 8) {
      toast.error('Password must be at least 8 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      toast.error('Passwords do not match.');
      return;
    }

    setIsRegistering(true);
    try {
      const result = await authService.register(
        fullName.trim(),
        invitation.invited_email,
        password,
        undefined,
        token
      );

      login(
        result.user,
        result.tokens.access_token,
        result.tokens.refresh_token,
        result.organization,
        [result.organization]
      );

      toast.success(`Welcome, ${result.user.name}! You have joined ${invitation.organization_name}.`);
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      toast.error(
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        'Failed to create account and join workspace.'
      );
    } finally {
      setIsRegistering(false);
    }
  };

  const handleSwitchAccount = () => {
    logout();
    navigate(`/login?invitation_token=${token}&email=${encodeURIComponent(invitation?.invited_email || '')}`);
  };

  const isEmailMatch =
    user && invitation && user.email.toLowerCase() === invitation.invited_email.toLowerCase();

  const roleDef = PREDEFINED_ROLES.find((r) => r.name === invitation?.role_name);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-background relative isolate">
      <div className="w-full max-w-lg space-y-6">
        {/* Top Branding */}
        <div className="text-center space-y-2">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-soft">
            <Building className="w-7 h-7" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Workspace Invitation</h1>
          <p className="text-sm text-muted-foreground">
            AI-Powered Application Security & Explainable Vulnerability Detection
          </p>
        </div>

        <Card className="border-border shadow-soft">
          <CardContent className="p-6 sm:p-8 space-y-6">
            {isLoading ? (
              <div className="py-16 flex flex-col items-center justify-center gap-3">
                <Spinner size="lg" />
                <p className="text-sm font-medium text-foreground">Verifying invitation token...</p>
                <p className="text-xs text-muted-foreground">Retrieving organization workspace details</p>
              </div>
            ) : errorDetails ? (
              /* Handled Error & Edge States */
              <div className="text-center py-6 space-y-5">
                <div className="w-14 h-14 mx-auto rounded-full bg-destructive/10 text-destructive flex items-center justify-center">
                  <AlertTriangle className="w-7 h-7" />
                </div>
                <div className="space-y-1.5 max-w-sm mx-auto">
                  <h3 className="text-lg font-semibold text-foreground">{errorDetails.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{errorDetails.message}</p>
                </div>
                <div className="pt-2 flex justify-center gap-3">
                  {isAuthenticated ? (
                    <Link to="/dashboard">
                      <Button variant="outline" size="sm">
                        Go to Dashboard
                      </Button>
                    </Link>
                  ) : (
                    <Link to="/login">
                      <Button variant="outline" size="sm">
                        Return to Sign In
                      </Button>
                    </Link>
                  )}
                </div>
              </div>
            ) : invitation ? (
              <div className="space-y-6">
                {/* Organization & Role Summary Card */}
                <div className="p-4 rounded-xl bg-muted/30 border border-border space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground font-medium">Workspace</span>
                    <span className="text-sm font-bold text-foreground flex items-center gap-1.5">
                      <Building className="w-4 h-4 text-primary" /> {invitation.organization_name}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground font-medium">Assigned Role</span>
                    <Badge
                      variant="outline"
                      className={`capitalize text-xs font-semibold px-2.5 py-0.5 border ${
                        roleDef ? roleDef.color : 'bg-primary/10 text-primary border-primary/30'
                      }`}
                    >
                      {roleDef ? roleDef.displayName : invitation.role_name.replace('_', ' ')}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground font-medium">Invited Email</span>
                    <span className="text-xs font-mono text-foreground flex items-center gap-1">
                      <Mail className="w-3.5 h-3.5 text-muted-foreground" /> {invitation.invited_email}
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-t border-border/40 pt-2 text-[11px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" /> Valid Until
                    </span>
                    <span>{new Date(invitation.expires_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                  </div>
                </div>

                {/* ── PATH 1: Existing Account ───────────────────────────── */}
                {invitation.account_exists ? (
                  <div className="space-y-4 pt-1">
                    {!isAuthenticated ? (
                      <div className="space-y-4">
                        <div className="p-3.5 rounded-lg bg-primary/5 border border-primary/20 text-xs text-muted-foreground leading-relaxed">
                          An account for <span className="font-semibold text-foreground">{invitation.invited_email}</span> already exists. Please sign in to accept this invitation.
                        </div>
                        <Button
                          className="w-full gap-2 h-11"
                          size="lg"
                          onClick={() =>
                            navigate(
                              `/login?invitation_token=${token}&email=${encodeURIComponent(
                                invitation.invited_email
                              )}`
                            )
                          }
                        >
                          <LogIn className="w-4 h-4" /> Sign in to accept invitation
                        </Button>
                      </div>
                    ) : !isEmailMatch ? (
                      /* Authenticated, but wrong email */
                      <div className="space-y-4">
                        <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300 space-y-1">
                          <div className="font-bold flex items-center gap-1.5">
                            <AlertTriangle className="w-4 h-4 text-amber-400" /> Account Mismatch
                          </div>
                          <p>
                            This invitation was sent to <span className="font-mono text-foreground font-semibold">{invitation.invited_email}</span>, but you are currently signed in as <span className="font-mono text-foreground font-semibold">{user?.email}</span>.
                          </p>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <Button
                            variant="outline"
                            onClick={handleSwitchAccount}
                            className="gap-1.5 text-xs"
                          >
                            <LogOut className="w-3.5 h-3.5" /> Switch Account
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => navigate('/dashboard')}
                            className="text-xs"
                          >
                            Go to Dashboard
                          </Button>
                        </div>
                      </div>
                    ) : (
                      /* Authenticated and email matches */
                      <div className="space-y-4">
                        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400 flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 shrink-0" />
                          <span>Signed in as <strong>{user?.name}</strong> ({user?.email})</span>
                        </div>
                        <Button
                          className="w-full gap-2 h-11"
                          size="lg"
                          onClick={handleAcceptExisting}
                          disabled={isAccepting}
                        >
                          {isAccepting ? (
                            <>
                              <Spinner size="sm" /> Joining Workspace...
                            </>
                          ) : (
                            <>
                              Accept Invitation & Join Workspace <ArrowRight className="w-4 h-4" />
                            </>
                          )}
                        </Button>
                      </div>
                    )}
                  </div>
                ) : (
                  /* ── PATH 2: New Account Registration ──────────────────── */
                  <div className="space-y-4 pt-1">
                    <div className="border-b border-border/60 pb-3">
                      <h2 className="text-base font-semibold text-foreground">
                        Create your account to join this workspace
                      </h2>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        You will be directly added to {invitation.organization_name} as {roleDef?.displayName || invitation.role_name}.
                      </p>
                    </div>

                    <form onSubmit={handleRegisterAndJoin} className="space-y-4">
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-foreground">Full Name</label>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <UserIcon className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <input
                            type="text"
                            required
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            className="w-full pl-10 h-10 bg-muted/30 border border-border rounded-lg text-sm text-foreground focus:ring-1 focus:ring-primary focus:border-primary transition-colors placeholder:text-muted-foreground/50"
                            placeholder="Alex Morgan"
                          />
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-foreground">Email Address</label>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <Mail className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <input
                            type="email"
                            readOnly
                            disabled
                            value={invitation.invited_email}
                            className="w-full pl-10 h-10 bg-muted/60 border border-border/60 rounded-lg text-sm font-mono text-muted-foreground cursor-not-allowed select-none"
                          />
                        </div>
                        <span className="text-[11px] text-muted-foreground">
                          Pre-filled and locked to invitation recipient
                        </span>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-foreground">Password (min. 8 characters)</label>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <Lock className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <input
                            type={showPassword ? 'text' : 'password'}
                            required
                            minLength={8}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full pl-10 pr-10 h-10 bg-background border border-border rounded-md text-xs text-foreground focus:ring-1 focus:ring-primary focus:border-primary transition-colors placeholder:text-muted-foreground/60"
                            placeholder="At least 8 characters"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground hover:text-foreground"
                            aria-label={showPassword ? 'Hide password' : 'Show password'}
                          >
                            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-foreground">Confirm Password</label>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <Lock className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <input
                            type={showConfirmPassword ? 'text' : 'password'}
                            required
                            minLength={8}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            className="w-full pl-10 pr-10 h-10 bg-background border border-border rounded-md text-xs text-foreground focus:ring-1 focus:ring-primary focus:border-primary transition-colors placeholder:text-muted-foreground/60"
                            placeholder="Re-enter password"
                          />
                          <button
                            type="button"
                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                            className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground hover:text-foreground"
                            aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                          >
                            {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                      </div>

                      <Button
                        type="submit"
                        className="w-full h-11 gap-2 mt-2"
                        disabled={isRegistering}
                      >
                        {isRegistering ? (
                          <>
                            <Spinner size="sm" /> Creating Account & Joining...
                          </>
                        ) : (
                          <>
                            <UserPlus className="w-4 h-4" /> Create account & Join workspace
                          </>
                        )}
                      </Button>
                    </form>
                  </div>
                )}
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

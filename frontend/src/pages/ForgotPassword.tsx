import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, Mail, ArrowLeft, KeyRound, ExternalLink, CheckCircle2, Copy, Check } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { authService } from '../services/authService';
import toast from 'react-hot-toast';

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [devResetUrl, setDevResetUrl] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setIsLoading(true);
    try {
      const response = await authService.requestPasswordReset(email.trim().toLowerCase());
      setIsSubmitted(true);

      // In local development, the backend provides dev_token and reset_url
      if (response?.reset_url) {
        setDevResetUrl(response.reset_url);
      } else if (response?.dev_token) {
        setDevResetUrl(`/reset-password?token=${response.dev_token}`);
      }
    } catch {
      // Security principle: Never reveal if email exists or fail loudly
      setIsSubmitted(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyDevLink = async () => {
    if (!devResetUrl) return;
    const fullUrl = `${window.location.origin}${devResetUrl}`;
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopiedLink(true);
      toast.success('Reset link copied to clipboard!');
      setTimeout(() => setCopiedLink(false), 2000);
    } catch {
      toast.error('Could not copy link to clipboard.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 relative isolate bg-background">
      <motion.div
        initial={{ opacity: 0, scale: 0.98, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <Link to="/" className="inline-block group space-y-3">
            <div className="w-12 h-12 mx-auto rounded-lg bg-primary flex items-center justify-center shadow-soft group-hover:scale-105 transition-transform">
              <ShieldCheck className="w-7 h-7 text-primary-foreground" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">VulnScan</h1>
          </Link>
          <p className="mt-1 text-xs text-muted-foreground">Account recovery and password reset</p>
        </div>

        <div className="bg-card rounded-lg p-8 sm:p-10 border border-border shadow-soft relative">
          {isSubmitted ? (
            <div className="space-y-5 text-center">
              <div className="w-10 h-10 mx-auto rounded-full bg-primary/10 text-primary flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-base font-semibold text-foreground">Check your inbox</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  If an active account matches that email address, a secure password reset link has been generated.
                </p>
              </div>

              {/* Development-only reset mechanism when SMTP is not configured */}
              {devResetUrl && (
                <div className="p-4 rounded-md bg-amber-500/10 border border-amber-500/30 text-left space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-amber-400 flex items-center gap-1.5 uppercase tracking-wider">
                      <KeyRound className="w-3.5 h-3.5" /> Local Dev Reset Link
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">
                      SMTP Offline
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    This local environment captured the single-use token directly. You can open or copy the reset URL:
                  </p>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => navigate(devResetUrl)}
                      className="flex-1 text-xs h-8 bg-amber-500 hover:bg-amber-600 text-black font-semibold gap-1.5"
                    >
                      <ExternalLink className="w-3.5 h-3.5" /> Open Reset Page
                    </Button>
                    <Button
                      onClick={handleCopyDevLink}
                      variant="outline"
                      className="text-xs h-8 border-amber-500/40 text-amber-300 hover:bg-amber-500/10 gap-1.5"
                    >
                      {copiedLink ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      {copiedLink ? 'Copied' : 'Copy Link'}
                    </Button>
                  </div>
                </div>
              )}

              <div className="pt-2 border-t border-border/50">
                <Link to="/login">
                  <Button variant="outline" className="w-full gap-2 text-xs h-9">
                    <ArrowLeft className="w-3.5 h-3.5" /> Return to Sign In
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Work Email Address</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 h-10 bg-background border border-border rounded-md text-xs text-foreground focus:ring-1 focus:ring-primary focus:border-primary transition-colors placeholder:text-muted-foreground/60"
                    placeholder="user@example.com"
                  />
                </div>
                <p className="text-[11px] text-muted-foreground">
                  A single-use password reset link will be issued.
                </p>
              </div>

              <Button
                type="submit"
                className="w-full h-10 text-xs font-semibold"
                disabled={isLoading}
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  'Send Reset Link'
                )}
              </Button>

              <div className="pt-3 border-t border-border/50 text-center">
                <Link
                  to="/login"
                  className="text-xs font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" /> Back to Sign In
                </Link>
              </div>
            </form>
          )}
        </div>
      </motion.div>
    </div>
  );
}

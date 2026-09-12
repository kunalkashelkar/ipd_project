import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, Mail, Lock } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { useAuthStore } from '../store';
import { authService } from '../services/authService';
import toast from 'react-hot-toast';

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const result = await authService.login(email, password);
      login(
        result.user,
        result.tokens.access_token,
        result.tokens.refresh_token
      );
      toast.success('Welcome back, ' + result.user.name + '!');
      navigate('/dashboard');
    } catch (err: any) {
      const message =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        'Login failed. Please check your credentials.';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 relative isolate bg-background">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <Link to="/" className="inline-block group space-y-4">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-primary flex items-center justify-center shadow-soft group-hover:scale-110 transition-transform">
              <ShieldCheck className="w-8 h-8 text-primary-foreground" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">XAI Tool</h1>
          </Link>
          <p className="mt-2 text-sm text-muted-foreground">Sign in to your enterprise workspace</p>
        </div>

        <div className="bg-card rounded-card p-8 sm:p-10 border border-border shadow-soft relative overflow-hidden">

          <form onSubmit={handleLogin} className="space-y-6 relative z-10">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Work Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 h-11 bg-muted/30 border border-border rounded-lg text-sm text-foreground focus:ring-1 focus:ring-primary focus:border-primary transition-colors placeholder:text-muted-foreground/50"
                  placeholder="admin@xaitool.io"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-foreground">Password</label>
                <a href="#" className="text-xs font-semibold text-primary hover:text-cyan-400 transition-colors">
                  Forgot password?
                </a>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-muted-foreground" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 h-11 bg-muted/30 border border-border rounded-lg text-sm text-foreground focus:ring-1 focus:ring-primary focus:border-primary transition-colors placeholder:text-muted-foreground/50"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full h-11 relative overflow-hidden group"
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <span className="font-semibold text-[15px]">Sign In</span>
              )}
            </Button>
          </form>

          <div className="mt-8 pt-6 border-t border-border/50 text-center relative z-10">
            <p className="text-sm text-muted-foreground">
              Don't have an organization account?{' '}
              <Link to="/register" className="font-semibold text-primary hover:text-cyan-400 transition-colors underline-offset-4 hover:underline">
                Request Access
              </Link>
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

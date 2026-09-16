import React, { useEffect, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { TopBar } from '../components/TopBar';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore } from '../store';
import { authStorage } from '../services/authStorage';
import { authService } from '../services/authService';
import { organizationService } from '../services/organizationService';
import { Spinner } from '../components/ui';

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    isAuthenticated,
    user,
    setUser,
    activeOrganization,
    setActiveOrganization,
    setActiveMemberRole,
    organizations,
    setOrganizations,
    logout,
  } = useAuthStore();
  const token = authStorage.getAccessToken();
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  // Auth guard — redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated || !token) {
      navigate('/login', { replace: true, state: { from: location } });
    }
  }, [isAuthenticated, token, navigate, location]);

  // Session & Organization Bootstrap — ensure authoritative user & valid active organization
  useEffect(() => {
    let isMounted = true;

    async function bootstrap() {
      if (!token) {
        setIsBootstrapping(false);
        return;
      }

      try {
        const meUser = await authService.getMe();
        if (!isMounted) return;
        setUser(meUser);

        // Fetch authoritative organizations for this user
        const orgs = await organizationService.listOrganizations();
        if (!isMounted) return;
        setOrganizations(orgs);

        // Validate or resolve active organization
        const storedOrgId = authStorage.getActiveOrganizationId();
        const matchedOrg = orgs.find((o) => o.id === storedOrgId);
        const resolvedOrg = matchedOrg || (orgs.length > 0 ? orgs[0] : null);

        if (resolvedOrg) {
          setActiveOrganization(resolvedOrg);
          authStorage.setActiveOrganizationId(resolvedOrg.id);
          const resolvedRole = resolvedOrg.current_user_role || (meUser as any)?.active_organization_role;
          if (resolvedRole) {
            setActiveMemberRole(resolvedRole);
          }
        } else {
          setActiveOrganization(null);
          setActiveMemberRole(null);
          authStorage.setActiveOrganizationId(null);
        }
      } catch (err: any) {
        if (err?.response?.status === 401) {
          authStorage.clearSession();
          logout();
          navigate('/login', { replace: true });
        }
      } finally {
        if (isMounted) {
          setIsBootstrapping(false);
        }
      }
    }

    bootstrap();
    return () => {
      isMounted = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return null; // Prevent flash of authenticated content
  }

  if (isBootstrapping) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-3">
        <Spinner size="lg" />
        <p className="text-xs text-muted-foreground font-medium">Initializing secure workspace...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-8 relative overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.15 }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

export function PublicLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const token = authStorage.getAccessToken();

  // If already logged in, redirect away from /login and /register to /dashboard
  useEffect(() => {
    if (isAuthenticated && token) {
      if (location.pathname === '/login' || location.pathname === '/register') {
        navigate('/dashboard', { replace: true });
      }
    }
  }, [isAuthenticated, token, location.pathname, navigate]);

  return (
    <div className="min-h-screen bg-background flex flex-col relative overflow-hidden">
      <main className="flex-1 flex flex-col relative z-10">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="flex-1 flex flex-col"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

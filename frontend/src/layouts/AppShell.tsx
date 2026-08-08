import React, { useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { TopBar } from '../components/TopBar';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore } from '../store';

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, token } = useAuthStore();

  // Auth guard — redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated || !token) {
      navigate('/login', { replace: true });
    }
  }, [isAuthenticated, token, navigate]);

  if (!isAuthenticated || !token) {
    return null; // Prevent flash of authenticated content
  }

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col">
        <TopBar />
        <main className="flex-1 p-8 relative overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
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
  return (
    <div className="min-h-screen bg-background flex flex-col relative overflow-hidden">

      <main className="flex-1 flex flex-col relative z-10">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="flex-1 flex flex-col"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

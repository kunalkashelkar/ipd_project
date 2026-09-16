import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Project, Notification, Organization } from './types';
import { authStorage } from './services/authStorage';

// ── Auth Store ────────────────────────────────────────────────

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  activeOrganization: Organization | null;
  activeMemberRole: string | null;
  organizations: Organization[];
  login: (user: User, accessToken: string, refreshToken: string, organization?: Organization, organizations?: Organization[]) => void;
  logout: () => void;
  setUser: (user: User) => void;
  setActiveOrganization: (org: Organization | null) => void;
  setActiveMemberRole: (role: string | null) => void;
  setOrganizations: (orgs: Organization[]) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      activeOrganization: null,
      activeMemberRole: null,
      organizations: [],
      login: (user, token, refreshToken, organization, organizations) => {
        if (organization) {
          authStorage.setActiveOrganizationId(organization.id);
        } else {
          authStorage.setActiveOrganizationId(null);
        }
        set({
          user,
          token,
          refreshToken,
          isAuthenticated: true,
          activeOrganization: organization || null,
          activeMemberRole: organization?.current_user_role || null,
          organizations: organizations || (organization ? [organization] : []),
        });
      },
      logout: () => {
        authStorage.clearSession();
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          activeOrganization: null,
          activeMemberRole: null,
          organizations: [],
        });
      },
      setUser: (user) => set({ user }),
      setActiveOrganization: (org) => {
        authStorage.setActiveOrganizationId(org ? org.id : null);
        set({
          activeOrganization: org,
          activeMemberRole: org?.current_user_role || null,
        });
      },
      setActiveMemberRole: (activeMemberRole) => set({ activeMemberRole }),
      setOrganizations: (organizations) => set({ organizations }),
    }),
    {
      name: 'auth-storage',
    }
  )
);

// ── Project Store ─────────────────────────────────────────────

interface ProjectState {
  projects: Project[];
  activeProjectId: string | null;
  setProjects: (projects: Project[]) => void;
  setActiveProject: (id: string | null) => void;
  addProject: (project: Project) => void;
  removeProject: (id: string) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  activeProjectId: null,
  setProjects: (projects) => set({ projects }),
  setActiveProject: (activeProjectId) => set({ activeProjectId }),
  addProject: (project) => set((state) => ({ projects: [...state.projects, project] })),
  removeProject: (id) => set((state) => ({ projects: state.projects.filter(p => p.id !== id) })),
}));

// ── Notification Store ────────────────────────────────────────

interface NotificationState {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  addNotification: (notif) => {
    const newNotif: Notification = {
      ...notif,
      id: Math.random().toString(36).substring(2, 9),
      timestamp: new Date().toISOString(),
      read: false,
    };
    set((state) => ({ notifications: [newNotif, ...state.notifications] }));
  },
  markAsRead: (id) => set((state) => ({
    notifications: state.notifications.map(n => n.id === id ? { ...n, read: true } : n)
  })),
  markAllAsRead: () => set((state) => ({
    notifications: state.notifications.map(n => ({ ...n, read: true }))
  })),
  removeNotification: (id) => set((state) => ({
    notifications: state.notifications.filter(n => n.id !== id)
  })),
}));

// ── Theme Store ───────────────────────────────────────────────

interface ThemeState {
  mode: 'light' | 'dark' | 'system';
  setMode: (mode: 'light' | 'dark' | 'system') => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      mode: 'dark',
      setMode: (mode) => set({ mode }),
    }),
    {
      name: 'theme-storage',
    }
  )
);

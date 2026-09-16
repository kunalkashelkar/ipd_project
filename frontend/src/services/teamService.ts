// ============================================================
// Team & Membership Service — Phase 2 Multi-Tenancy RBAC
// ============================================================

import apiClient from './api';
import { OrganizationMember, OrganizationInvitation, RoleWithPermissions } from '../types';

export interface InvitationPreview {
  id: string;
  organization_id: string;
  organization_name: string;
  invited_email: string;
  role_name: string;
  expires_at: string;
  status: string;
  account_exists?: boolean;
  already_member?: boolean;
}

export const teamService = {
  async listMembers(orgId: string): Promise<OrganizationMember[]> {
    const response = await apiClient.get<OrganizationMember[]>(
      `/organizations/${orgId}/team/members`
    );
    return response.data;
  },

  async inviteMember(
    orgId: string,
    email: string,
    roleName: string
  ): Promise<OrganizationInvitation> {
    const response = await apiClient.post<OrganizationInvitation>(
      `/organizations/${orgId}/team/invitations`,
      {
        email,
        role_name: roleName,
      }
    );
    return response.data;
  },

  async listInvitations(orgId: string): Promise<OrganizationInvitation[]> {
    const response = await apiClient.get<OrganizationInvitation[]>(
      `/organizations/${orgId}/team/invitations`
    );
    return response.data;
  },

  async changeMemberRole(
    orgId: string,
    memberUserId: string,
    roleName: string
  ): Promise<OrganizationMember> {
    const response = await apiClient.patch<OrganizationMember>(
      `/organizations/${orgId}/team/members/${memberUserId}/role`,
      {
        role_name: roleName,
      }
    );
    return response.data;
  },

  async removeMember(orgId: string, memberUserId: string): Promise<void> {
    await apiClient.delete(`/organizations/${orgId}/team/members/${memberUserId}`);
  },

  async listRoles(orgId: string): Promise<RoleWithPermissions[]> {
    const response = await apiClient.get<RoleWithPermissions[]>(
      `/organizations/${orgId}/team/roles`
    );
    return response.data;
  },

  async getInvitationDetails(token: string): Promise<InvitationPreview> {
    const response = await apiClient.get<InvitationPreview>(`/invitations/${token}`);
    return response.data;
  },

  async acceptInvitation(token: string): Promise<OrganizationMember> {
    const response = await apiClient.post<OrganizationMember>('/invitations/accept', {
      token,
    });
    return response.data;
  },
};


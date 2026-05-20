// frontend/crm-app/src/app/services/admin.service.ts
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { OnlinePayment, OnlinePaymentMethodType } from './payments.service';
import {
  Permission,
  Role,
  Shop,
  SubscriptionPlan,
  SubscriptionStatus,
  User,
} from '../core/models/models';

export interface UserCreateRequest {
  username: string;
  password: string;
  first_name: string;
  last_name: string;
  middle_name?: string;
  email: string;
  phone?: string;
  role_id?: number;
  shop_ids: number[];
  is_director?: boolean;
  can_field_visit?: boolean;
  profile_status?: string;
  bio?: string;
  compensation_type?: 'fixed' | 'commission' | 'mixed';
  fixed_order_payment?: number;
  service_commission_percent?: number;
  product_commission_percent?: number;
}

export interface UserUpdateRequest {
  first_name?: string;
  last_name?: string;
  middle_name?: string;
  email?: string;
  phone?: string;
  role_id?: number;
  shop_ids?: number[];
  is_director?: boolean;
  can_field_visit?: boolean;
  is_active?: boolean;
  profile_status?: string;
  bio?: string;
  compensation_type?: 'fixed' | 'commission' | 'mixed';
  fixed_order_payment?: number;
  service_commission_percent?: number;
  product_commission_percent?: number;
}

export interface ShopCreateRequest {
  name: string;
  code: string;
  city?: string;
  address?: string;
  latitude?: number | null;
  longitude?: number | null;
  phone?: string;
  email?: string;
  timezone: string;
  currency: string;
}

export interface ClientPortalIntegration {
  id: number;
  organization_id: number;
  organization_name: string;
  enabled: boolean;
  configured: boolean;
  base_url?: string | null;
  tenant_key: string;
  client_domain?: string | null;
  auth_policy: 'phone_or_email' | 'phone_only' | 'email_only' | string;
  support_phone?: string | null;
  support_email?: string | null;
  brand_name?: string | null;
  accent_color?: string | null;
  portal_banner_enabled: boolean;
  portal_banner_title?: string | null;
  portal_banner_subtitle?: string | null;
  portal_banner_image_url?: string | null;
  portal_banner_link_url?: string | null;
  api_key_configured: boolean;
  last_push_at?: string | null;
  last_pull_at?: string | null;
  last_error?: string | null;
  field_visit?: Record<string, unknown> | null;
  landing?: ClientLandingConfig | null;
}

export interface ClientLandingCard {
  title: string;
  body: string;
  icon: string;
}

export interface ClientLandingPromoSpotlight {
  enabled: boolean;
  title: string;
  subtitle: string;
  body: string;
  badge: string;
  cta_label: string;
  cta_href: string;
  image_url?: string | null;
}

export interface ClientLandingConfig {
  section_eyebrow: string;
  section_title: string;
  section_subtitle: string;
  feature_cards: ClientLandingCard[];
  promo_spotlight: ClientLandingPromoSpotlight;
}

export interface ClientLandingPatchRequest {
  landing_section_eyebrow?: string;
  landing_section_title?: string;
  landing_section_subtitle?: string;
  feature_cards?: ClientLandingCard[];
  promo_spotlight?: Partial<ClientLandingPromoSpotlight>;
}

export type ClientPortalIntegrationUpdate = Partial<
  Pick<
    ClientPortalIntegration,
    | 'enabled'
    | 'base_url'
    | 'tenant_key'
    | 'client_domain'
    | 'auth_policy'
    | 'support_phone'
    | 'support_email'
    | 'brand_name'
    | 'accent_color'
    | 'portal_banner_enabled'
    | 'portal_banner_title'
    | 'portal_banner_subtitle'
    | 'portal_banner_image_url'
    | 'portal_banner_link_url'
  >
> & {
  api_key?: string;
};

export interface ClientSyncStatus {
  integration: ClientPortalIntegration;
  order_states: Record<string, number>;
  actions: Record<string, number>;
}

export interface ClientSyncRunResult {
  pushed: number;
  skipped: number;
  pulled: number;
  applied: number;
  errors: number;
}

export interface ClientSyncAction {
  id: number;
  external_id: string;
  action_type: string;
  status: string;
  related_order_id?: number | null;
  related_task_id?: number | null;
  error_message?: string | null;
  received_at: string;
  applied_at?: string | null;
  synced_back_at?: string | null;
}

export interface AdminAgentStatus {
  configured: boolean;
  heartbeat_enabled: boolean;
  enforcement: {
    enabled: boolean;
    require_sync: boolean;
    stale_grace_hours: number;
    superuser_bypass: boolean;
  };
  last_synced_at?: string | null;
  last_error_at?: string | null;
  last_error_message?: string | null;
  subscription?: {
    status?: string;
    access_allowed?: boolean;
    reason?: string;
    paid_until?: string | null;
    trial_until?: string | null;
    grace_until?: string | null;
    plan_code?: string | null;
    plan_name?: string | null;
    features?: Record<string, unknown>;
    limits?: Record<string, unknown>;
  } | null;
  campaigns: Array<Record<string, unknown>>;
  support_unread: number;
}

export interface AdminSupportThread {
  id: number;
  client_id: number;
  installation_id?: number | null;
  client_name?: string | null;
  subject: string;
  status: string;
  priority: string;
  last_message_at?: string | null;
  unread_admin: number;
  unread_client: number;
  created_at: string;
  updated_at: string;
}

export interface AdminSupportMessage {
  id: number;
  thread_id: number;
  author_type: 'admin' | 'client' | 'system' | string;
  admin_user_id?: number | null;
  external_author?: string | null;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface AdminSupportThreadCreateRequest {
  subject: string;
  priority: string;
  body: string;
  author_name?: string | null;
}

export interface AdminSupportMessageCreateRequest {
  body: string;
  author_name?: string | null;
}

@Injectable({
  providedIn: 'root',
})
export class AdminService {
  constructor(private apiService: ApiService) {}

  // Users Management
  getUsers(page: number = 1, pageSize: number = 20): Observable<User[]> {
    return this.apiService.get<User[]>('/admin/users', { page, page_size: pageSize });
  }

  getUserOptions(limit: number = 200): Observable<User[]> {
    return this.apiService.get<User[]>('/admin/users/options', {
      limit,
      active_only: true,
    });
  }

  getUser(id: number): Observable<User> {
    return this.apiService.get<User>(`/admin/users/${id}`);
  }

  createUser(userData: UserCreateRequest): Observable<User> {
    return this.apiService.post<User>('/admin/users', userData);
  }

  updateUser(id: number, userData: UserUpdateRequest): Observable<User> {
    return this.apiService.put<User>(`/admin/users/${id}`, userData);
  }

  deleteUser(id: number): Observable<any> {
    return this.apiService.delete(`/admin/users/${id}`);
  }

  resetUserPassword(id: number, newPassword: string): Observable<any> {
    return this.apiService.post(`/admin/users/${id}/reset-password`, { password: newPassword });
  }

  // Shops Management
  getShops(): Observable<Shop[]> {
    return this.apiService.get<Shop[]>('/admin/shops');
  }

  getShop(id: number): Observable<Shop> {
    return this.apiService.get<Shop>(`/admin/shops/${id}`);
  }

  createShop(shopData: ShopCreateRequest): Observable<Shop> {
    return this.apiService.post<Shop>('/admin/shops', shopData);
  }

  updateShop(id: number, shopData: Partial<ShopCreateRequest>): Observable<Shop> {
    return this.apiService.put<Shop>(`/admin/shops/${id}`, shopData);
  }

  deleteShop(id: number): Observable<any> {
    return this.apiService.delete(`/admin/shops/${id}`);
  }

  // Roles Management
  getRoles(): Observable<Role[]> {
    return this.apiService.get<Role[]>('/admin/roles');
  }

  getRole(id: number): Observable<Role> {
    return this.apiService.get<Role>(`/admin/roles/${id}`);
  }

  createRole(roleData: {
    name: string;
    code: string;
    description?: string;
    permission_ids: number[];
  }): Observable<Role> {
    return this.apiService.post<Role>('/admin/roles', roleData);
  }

  updateRole(
    id: number,
    roleData: Partial<{
      name: string;
      code: string;
      description?: string;
      permission_ids: number[];
    }>,
  ): Observable<Role> {
    return this.apiService.put<Role>(`/admin/roles/${id}`, roleData);
  }

  deleteRole(id: number): Observable<any> {
    return this.apiService.delete(`/admin/roles/${id}`);
  }

  // Permissions Management
  getPermissions(): Observable<Permission[]> {
    return this.apiService.get<Permission[]>('/admin/permissions');
  }

  // System Statistics
  getSystemStatistics(allShops = false): Observable<any> {
    if (allShops) {
      return this.apiService.get<any>('/admin/statistics', { all_shops: true });
    }

    return this.apiService.get<any>('/admin/statistics');
  }

  getEmployeesStatistics(params?: Record<string, unknown>): Observable<any> {
    return this.apiService.get<any>('/admin/employees/statistics', params);
  }

  getSubscriptionStatus(): Observable<SubscriptionStatus> {
    return this.apiService.get<SubscriptionStatus>('/shops/subscription/status');
  }

  getSubscriptionPlans(): Observable<SubscriptionPlan[]> {
    return this.apiService.get<SubscriptionPlan[]>('/shops/subscription/plans');
  }

  changeSubscription(planCode: string): Observable<SubscriptionStatus> {
    return this.apiService.post<SubscriptionStatus>('/shops/subscription/change', {
      plan_code: planCode,
    });
  }

  createSubscriptionPayment(
    planCode: string,
    paymentMethodType: OnlinePaymentMethodType,
  ): Observable<OnlinePayment> {
    return this.apiService.post<OnlinePayment>('/shops/subscription/pay', {
      plan_code: planCode,
      payment_method_type: paymentMethodType,
    });
  }

  getClientSyncStatus(): Observable<ClientSyncStatus> {
    return this.apiService.get<ClientSyncStatus>('/client-sync/status');
  }

  updateClientSyncIntegration(
    data: ClientPortalIntegrationUpdate,
  ): Observable<ClientPortalIntegration> {
    return this.apiService.put<ClientPortalIntegration>('/client-sync/integration', data);
  }

  runClientSync(push = true, pull = true, limit = 100): Observable<ClientSyncRunResult> {
    return this.apiService.post<ClientSyncRunResult>('/client-sync/run', {
      push,
      pull,
      limit,
    });
  }

  getClientSyncActions(limit = 20): Observable<ClientSyncAction[]> {
    return this.apiService.get<ClientSyncAction[]>('/client-sync/actions', { limit });
  }

  getClientLanding(): Observable<ClientLandingConfig> {
    return this.apiService.get<ClientLandingConfig>('/client-sync/landing');
  }

  patchClientLanding(data: ClientLandingPatchRequest): Observable<ClientLandingConfig> {
    return this.apiService.patch<ClientLandingConfig>('/client-sync/landing', data);
  }

  getAdminAgentStatus(): Observable<AdminAgentStatus> {
    return this.apiService.get<AdminAgentStatus>('/admin-agent/status');
  }

  sendAdminAgentHeartbeat(): Observable<Record<string, unknown>> {
    return this.apiService.post<Record<string, unknown>>('/admin-agent/heartbeat', {});
  }

  getAdminSupportThreads(): Observable<AdminSupportThread[]> {
    return this.apiService.get<AdminSupportThread[]>('/admin-agent/support/threads');
  }

  createAdminSupportThread(
    data: AdminSupportThreadCreateRequest,
  ): Observable<AdminSupportThread> {
    return this.apiService.post<AdminSupportThread>('/admin-agent/support/threads', data);
  }

  getAdminSupportMessages(threadId: number): Observable<AdminSupportMessage[]> {
    return this.apiService.get<AdminSupportMessage[]>(
      `/admin-agent/support/threads/${threadId}/messages`,
    );
  }

  replyAdminSupportThread(
    threadId: number,
    data: AdminSupportMessageCreateRequest,
  ): Observable<AdminSupportMessage> {
    return this.apiService.post<AdminSupportMessage>(
      `/admin-agent/support/threads/${threadId}/messages`,
      data,
    );
  }
}

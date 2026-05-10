export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  middle_name?: string;
  email: string;
  phone?: string;
  is_director: boolean;
  is_active: boolean;
  current_shop?: Shop;
  available_shops?: Shop[];
  avatar?: string;
  profile_status?: string;
  bio?: string;
  compensation_type?: 'fixed' | 'commission' | 'mixed';
  fixed_order_payment?: number;
  service_commission_percent?: number;
  product_commission_percent?: number;
  role?: Role;
  shops?: Shop[];
  last_login?: string;
}

export interface Shop {
  id: number;
  name: string;
  code: string;
  city?: string;
  address?: string;
  latitude?: number | null;
  longitude?: number | null;
  phone?: string;
  email?: string;
  is_active: boolean;
  timezone: string;
  currency: string;
}

export interface SubscriptionPlan {
  code: string;
  name: string;
  billing_period: string;
  duration_days: number;
  price: number;
}

export interface SubscriptionStatus {
  organization_id: number;
  organization_name: string;
  plan: SubscriptionPlan;
  status: string;
  status_display: string;
  started_at: string;
  expires_at: string;
  remaining_days: number;
  remaining_percent: number;
  color_bucket: number;
  color_hex: string;
  is_expired: boolean;
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
  is_active?: boolean;
  timezone: string;
  currency: string;
}

export interface Role {
  id: number;
  name: string;
  code: string;
  description?: string;
  permission_codes?: string[];
  permissions_count?: number;
  permissions?: Permission[];
}

export interface Customer {
  id: number;
  first_name: string;
  last_name: string;
  middle_name?: string;
  phone: string;
  email?: string;
  source?: string;
  source_details?: string;
  birth_date?: string;
  notes?: string;
  preferred_channel?: string;
  marketing_consent: boolean; // Обязательно в backend
  orders_count: number;
  total_spent: number;
  created_at: string;
  updated_at: string;
}

export type CustomerPayload = Partial<Omit<Customer, 'birth_date'>> & {
  birth_date?: string | null;
};

export interface DeviceBrand {
  id: number;
  name: string;
}

export interface DeviceType {
  id: number;
  name: string;
  icon?: string;
}

export interface DeviceModel {
  id: number;
  brand: DeviceBrand;
  device_type: DeviceType;
  name: string;
  model_number?: string;
  release_year?: number;
}

export interface Device {
  id: number;
  model: DeviceModel;
  serial_number?: string;
  imei?: string;
  color?: string;
  storage_capacity?: string;
  specifications?: any;
}

export interface AdditionalService {
  id: number;
  name: string;
  category: string;
  description?: string;
  price: number;
  is_active?: boolean;
  shop_ids?: number[];
}

export interface OrderService {
  service: AdditionalService;
  quantity: number;
  price: number;
  total_price: number;
}

export interface OrderDiscount {
  id: number;
  source: 'manual' | 'promo_code' | 'auto' | 'loyalty';
  label: string;
  amount: number;
  promotion_id?: number;
  promotion_name?: string;
  promo_code_id?: number;
  promo_code?: string;
  created_at: string;
}

export interface Order {
  id: number;
  order_number: string;
  customer: Customer;
  device: Device;
  status: OrderStatus;
  priority: OrderPriority;
  problem_description: string;
  diagnosis?: string;
  work_description?: string;
  accessories?: string;
  device_condition?: string;
  cost_estimate: number;
  final_cost?: number;
  prepayment: number; // Обязательно в backend
  subtotal_before_discount?: number;
  discount_total?: number;
  total_cost: number; // Обязательно в backend
  remaining_payment: number; // Обязательно в backend
  created_at: string;
  updated_at: string;
  estimated_completion?: string;
  completed_at?: string;
  additional_services: OrderService[];
  discounts?: OrderDiscount[];
  notes?: string;
  warranty_days?: number;
  warranty_until?: string;
  warranty_active?: boolean;
  is_warranty_case?: boolean;
  warranty_parent_order_id?: number;
  warranty_parent_order_number?: string;
  warranty_reason?: string;
  warranty_resolution?: string;
  warranty_cases_count?: number;
}

export interface Promotion {
  id: number;
  name: string;
  description?: string;
  discount_type: 'percent' | 'fixed';
  value: number;
  max_discount_amount?: number | null;
  min_order_amount: number;
  starts_at?: string | null;
  ends_at?: string | null;
  is_active: boolean;
  auto_apply: boolean;
  stackable: boolean;
  usage_limit?: number | null;
  per_customer_limit?: number | null;
  shop_ids: number[];
  used_count: number;
  created_at: string;
  updated_at: string;
}

export interface PromoCode {
  id: number;
  promotion_id: number;
  promotion_name: string;
  code: string;
  description?: string;
  is_active: boolean;
  starts_at?: string | null;
  ends_at?: string | null;
  usage_limit?: number | null;
  per_customer_limit?: number | null;
  used_count: number;
  created_at: string;
  updated_at: string;
}

export interface DiscountQuote {
  valid: boolean;
  message: string;
  code?: string;
  promotion_id?: number;
  promotion_name?: string;
  subtotal: number;
  discount_amount: number;
  total_after_discount: number;
}

export interface WarrantyCaseCreate {
  reason: string;
  problem_description?: string;
  priority?: OrderPriority;
  estimated_completion?: string | null;
}

export interface OrderStatusHistory {
  id: number;
  old_status?: OrderStatus;
  new_status: OrderStatus;
  comment?: string;
  changed_by_name?: string;
  changed_at: string;
}

export interface OrderAuditLog {
  id: number;
  action: string;
  message: string;
  changes: Record<string, unknown>;
  actor_name?: string;
  created_at: string;
}

export interface RepairStage {
  id: number;
  title: string;
  description?: string;
  photo_url?: string;
  customer_visible: boolean;
  position: number;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface OrderApproval {
  id: number;
  title: string;
  description?: string;
  amount: number;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  status_display: string;
  customer_comment?: string;
  requested_by_name?: string;
  decided_at?: string;
  created_at: string;
  updated_at: string;
}

export type OrderStatus =
  | 'received'
  | 'diagnosed'
  | 'waiting_parts'
  | 'in_repair'
  | 'testing'
  | 'ready'
  | 'completed'
  | 'cancelled';

export type OrderPriority = 'low' | 'normal' | 'high' | 'urgent';

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface OrderFilters {
  search?: string;
  status?: OrderStatus;
  priority?: OrderPriority;
  customer_id?: number;
  assigned_to_id?: number;
  created_from?: string;
  created_to?: string;
  estimated_completion_from?: string;
  estimated_completion_to?: string;
}

export interface CustomerFilters {
  search?: string;
  source?: string;
  created_from?: string;
  created_to?: string;
  has_orders?: boolean;
}

export interface Permission {
  id: number;
  name: string;
  code: string;
  codename?: string;
  description?: string;
  category: string;
  category_label?: string;
}

export interface UserFilters {
  search?: string;
  role?: string;
  is_active?: boolean;
  shop_id?: number;
}

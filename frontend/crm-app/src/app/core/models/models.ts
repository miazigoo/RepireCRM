export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  middle_name?: string;
  email: string;
  phone?: string;
  is_director: boolean;
  current_shop?: Shop;
  avatar?: string;
  role?: Role;
}

export interface Shop {
  id: number;
  name: string;
  code: string;
  address?: string;
  phone?: string;
  email?: string;
  is_active: boolean;
  timezone: string;
  currency: string;
}

export interface Role {
  id: number;
  name: string;
  code: string;
  description?: string;
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
  orders_count: number;
  total_spent: number;
  created_at: string;
  updated_at: string;
}

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
}

export interface OrderService {
  service: AdditionalService;
  quantity: number;
  price: number;
  total_price: number;
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
  prepayment: number;
  total_cost: number;
  remaining_payment: number;
  created_at: string;
  updated_at: string;
  estimated_completion?: string;
  completed_at?: string;
  additional_services: OrderService[];
  notes?: string;
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
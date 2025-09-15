// frontend/crm-app/src/app/services/admin.service.ts
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { User, Shop, Role, Permission } from '../core/models/models';

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
  is_active?: boolean;
}

export interface ShopCreateRequest {
  name: string;
  code: string;
  address?: string;
  phone?: string;
  email?: string;
  timezone: string;
  currency: string;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  constructor(private apiService: ApiService) {}

  // Users Management
  getUsers(page: number = 1, pageSize: number = 20): Observable<User[]> {
    return this.apiService.get<User[]>('/admin/users', { page, page_size: pageSize });
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

  createRole(roleData: { name: string; code: string; description?: string; permission_ids: number[] }): Observable<Role> {
    return this.apiService.post<Role>('/admin/roles', roleData);
  }

  updateRole(id: number, roleData: Partial<{ name: string; code: string; description?: string; permission_ids: number[] }>): Observable<Role> {
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
  getSystemStatistics(): Observable<any> {
    return this.apiService.get<any>('/admin/statistics');
  }
}

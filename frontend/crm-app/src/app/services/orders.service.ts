import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { ApiService } from './api.service';
import {
  AdditionalService,
  DeviceModel,
  Order,
  OrderApproval,
  OrderAuditLog,
  OrderFilters,
  PaginatedResponse,
  OrderStatusHistory,
  RepairStage
} from '../core/models/models';

type OrderListResponse = Order[] | PaginatedResponse<Order>;

@Injectable({
  providedIn: 'root'
})
export class OrdersService {
  private endpoint = '/orders';

  constructor(private apiService: ApiService) {}

  getOrders(page: number = 1, pageSize: number = 20, filters?: OrderFilters): Observable<Order[]> {
    const params = {
      page,
      page_size: pageSize,
      ...filters
    };
    return this.apiService.get<OrderListResponse>(this.endpoint, params).pipe(
      map(response => Array.isArray(response) ? response : response.items)
    );
  }

  getOrder(id: number): Observable<Order> {
    return this.apiService.get<Order>(`${this.endpoint}/${id}`);
  }

  createOrder(order: any): Observable<Order> {
    return this.apiService.post<Order>(`${this.endpoint}/`, order);
  }

  updateOrder(id: number, order: Partial<Order>): Observable<Order> {
    return this.apiService.put<Order>(`${this.endpoint}/${id}`, order);
  }

  getStatusHistory(id: number): Observable<OrderStatusHistory[]> {
    return this.apiService.get<OrderStatusHistory[]>(`${this.endpoint}/${id}/status-history`);
  }

  getAuditLog(id: number): Observable<OrderAuditLog[]> {
    return this.apiService.get<OrderAuditLog[]>(`${this.endpoint}/${id}/audit-log`);
  }

  getRepairStages(id: number): Observable<RepairStage[]> {
    return this.apiService.get<RepairStage[]>(`${this.endpoint}/${id}/repair-stages`);
  }

  addRepairStage(id: number, data: FormData): Observable<RepairStage> {
    return this.apiService.postForm<RepairStage>(`${this.endpoint}/${id}/repair-stages`, data);
  }

  getApprovals(id: number): Observable<OrderApproval[]> {
    return this.apiService.get<OrderApproval[]>(`${this.endpoint}/${id}/approvals`);
  }

  requestApproval(
    id: number,
    data: { title: string; description?: string; amount: number }
  ): Observable<OrderApproval> {
    return this.apiService.post<OrderApproval>(`${this.endpoint}/${id}/approvals`, data);
  }

  getAdditionalServices(): Observable<AdditionalService[]> {
    return this.apiService.get<AdditionalService[]>(`${this.endpoint}/additional-services`);
  }

  getDeviceModels(): Observable<DeviceModel[]> {
    return this.apiService.get<DeviceModel[]>(`${this.endpoint}/device-models`);
  }

  createDeviceModel(data: {
    brand_name: string;
    name: string;
    device_type_name?: string;
    model_number?: string;
    release_year?: number;
  }): Observable<DeviceModel> {
    return this.apiService.post<DeviceModel>(`${this.endpoint}/device-models`, data);
  }

  getStatistics(): Observable<any> {
    return this.apiService.get<any>(`${this.endpoint}/statistics`);
  }
}

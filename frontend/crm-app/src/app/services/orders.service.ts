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
  RepairStage,
  WarrantyCaseCreate
} from '../core/models/models';

type OrderListResponse = Order[] | PaginatedResponse<Order>;
type OrderUpdatePayload = Partial<Order> & { status_comment?: string };

@Injectable({
  providedIn: 'root'
})
export class OrdersService {
  private endpoint = '/orders';

  constructor(private apiService: ApiService) {}

  getOrdersPage(
    page: number = 1,
    pageSize: number = 20,
    filters?: OrderFilters
  ): Observable<PaginatedResponse<Order>> {
    const rawParams = {
      page,
      page_size: pageSize,
      ...filters
    };
    const params = Object.fromEntries(
      Object.entries(rawParams).filter(([, value]) => value !== '' && value !== null && value !== undefined)
    );

    return this.apiService.get<OrderListResponse>(this.endpoint, params).pipe(
      map(response => Array.isArray(response)
        ? {
          items: response,
          count: response.length,
          page,
          page_size: pageSize,
          total_pages: 1
        }
        : response)
    );
  }

  getOrders(page: number = 1, pageSize: number = 20, filters?: OrderFilters): Observable<Order[]> {
    return this.getOrdersPage(page, pageSize, filters).pipe(
      map(response => response.items)
    );
  }

  getOrder(id: number): Observable<Order> {
    return this.apiService.get<Order>(`${this.endpoint}/${id}`);
  }

  createOrder(order: any): Observable<Order> {
    return this.apiService.post<Order>(`${this.endpoint}/`, order);
  }

  updateOrder(id: number, order: OrderUpdatePayload): Observable<Order> {
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

  getWarrantyCases(id: number): Observable<Order[]> {
    return this.apiService.get<Order[]>(`${this.endpoint}/${id}/warranty-cases`);
  }

  createWarrantyCase(id: number, data: WarrantyCaseCreate): Observable<Order> {
    return this.apiService.post<Order>(`${this.endpoint}/${id}/warranty-cases`, data);
  }

  getAdditionalServices(includeInactive = false): Observable<AdditionalService[]> {
    const params = includeInactive ? { include_inactive: true } : undefined;
    return this.apiService.get<AdditionalService[]>(`${this.endpoint}/additional-services`, params);
  }

  createAdditionalService(data: Partial<AdditionalService> & { shop_ids?: number[] }): Observable<AdditionalService> {
    return this.apiService.post<AdditionalService>(`${this.endpoint}/additional-services`, data);
  }

  updateAdditionalService(id: number, data: Partial<AdditionalService> & { shop_ids?: number[] }): Observable<AdditionalService> {
    return this.apiService.put<AdditionalService>(`${this.endpoint}/additional-services/${id}`, data);
  }

  deleteAdditionalService(id: number): Observable<{ success: boolean }> {
    return this.apiService.delete<{ success: boolean }>(`${this.endpoint}/additional-services/${id}`);
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

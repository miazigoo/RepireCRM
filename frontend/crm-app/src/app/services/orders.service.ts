import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import {
  AdditionalService,
  Order,
  OrderAuditLog,
  OrderFilters,
  OrderStatusHistory,
  RepairStage
} from '../core/models/models';

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
    return this.apiService.get<Order[]>(this.endpoint, params);
  }

  getOrder(id: number): Observable<Order> {
    return this.apiService.get<Order>(`${this.endpoint}/${id}`);
  }

  createOrder(order: any): Observable<Order> {
    return this.apiService.post<Order>(this.endpoint, order);
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

  getAdditionalServices(): Observable<AdditionalService[]> {
    return this.apiService.get<AdditionalService[]>(`${this.endpoint}/additional-services`);
  }

  getStatistics(): Observable<any> {
    return this.apiService.get<any>(`${this.endpoint}/statistics`);
  }
}

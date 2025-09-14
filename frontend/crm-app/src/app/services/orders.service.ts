import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Order, OrderFilters, AdditionalService } from '../core/models/models';

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

  getAdditionalServices(): Observable<AdditionalService[]> {
    return this.apiService.get<AdditionalService[]>(`${this.endpoint}/additional-services`);
  }

  getStatistics(): Observable<any> {
    return this.apiService.get<any>(`${this.endpoint}/statistics`);
  }
}
import { Injectable } from '@angular/core';
import { Observable, of, delay } from 'rxjs';
import { Order, OrderFilters, AdditionalService } from '../core/models/models';

@Injectable({
  providedIn: 'root'
})
export class MockOrdersService {
  getOrders(page: number = 1, pageSize: number = 20, filters?: OrderFilters): Observable<Order[]> {
    return of([]).pipe(delay(500));
  }

  getOrder(id: number): Observable<Order> {
    const mockOrder = {
      id: 1,
      order_number: 'MSK-000001',
      customer: {
        id: 1,
        first_name: 'Иван',
        last_name: 'Петров',
        phone: '+7 (999) 123-45-67',
        email: 'petrov@example.com',
        orders_count: 1,
        total_spent: 5000,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z'
      },
      device: {
        id: 1,
        model: {
          id: 1,
          brand: { id: 1, name: 'Apple' },
          device_type: { id: 1, name: 'Смартфон' },
          name: 'iPhone 15 Pro'
        },
        color: 'Черный',
        storage_capacity: '256GB'
      },
      status: 'received' as any,
      priority: 'normal' as any,
      problem_description: 'Разбит экран',
      cost_estimate: 15000,
      prepayment: 5000,
      total_cost: 15000,
      remaining_payment: 10000,
      created_at: '2024-01-15T10:00:00Z',
      updated_at: '2024-01-15T10:00:00Z',
      additional_services: []
    };
    return of(mockOrder).pipe(delay(500));
  }

  createOrder(order: any): Observable<Order> {
    return of({ id: 1 } as any).pipe(delay(1000));
  }

  updateOrder(id: number, order: Partial<Order>): Observable<Order> {
    return of({ id } as any).pipe(delay(1000));
  }

  getAdditionalServices(): Observable<AdditionalService[]> {
    return of([]).pipe(delay(500));
  }

  getStatistics(): Observable<any> {
    return of({
      total_orders: 0,
      total_revenue: 0,
      avg_order_value: 0,
      recent_orders: 0,
      recent_revenue: 0,
      status_distribution: []
    }).pipe(delay(500));
  }
}

import { Injectable } from '@angular/core';
import { Observable, of, delay } from 'rxjs';
import { Customer, CustomerFilters } from '../core/models/models';

@Injectable({
  providedIn: 'root'
})
export class MockCustomersService {
  getCustomers(page: number = 1, pageSize: number = 20, filters?: CustomerFilters): Observable<Customer[]> {
    return of([]).pipe(delay(500));
  }

  getCustomer(id: number): Observable<Customer> {
    const mockCustomer: Customer = {
      id: 1,
      first_name: 'Иван',
      last_name: 'Петров',
      phone: '+7 (999) 123-45-67',
      email: 'petrov@example.com',
      orders_count: 1,
      total_spent: 5000,
      created_at: '2024-01-15T10:00:00Z',
      updated_at: '2024-01-15T10:00:00Z'
    };
    return of(mockCustomer).pipe(delay(500));
  }

  createCustomer(customer: Partial<Customer>): Observable<Customer> {
    return of({ id: 1 } as any).pipe(delay(1000));
  }

  updateCustomer(id: number, customer: Partial<Customer>): Observable<Customer> {
    return of({ id } as any).pipe(delay(1000));
  }

  deleteCustomer(id: number): Observable<any> {
    return of({ success: true }).pipe(delay(500));
  }

  getCustomerOrders(id: number): Observable<any[]> {
    return of([]).pipe(delay(500));
  }
}

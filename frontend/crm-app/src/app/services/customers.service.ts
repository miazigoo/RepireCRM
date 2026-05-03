import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { ApiService } from './api.service';
import { Customer, CustomerFilters, PaginatedResponse } from '../core/models/models';

type CustomerListResponse = Customer[] | PaginatedResponse<Customer>;

@Injectable({
  providedIn: 'root'
})
export class CustomersService {
  private endpoint = '/customers';

  constructor(private apiService: ApiService) {}

  getCustomers(page: number = 1, pageSize: number = 20, filters?: CustomerFilters): Observable<Customer[]> {
    const rawParams = {
      page,
      page_size: pageSize,
      ...filters
    };
    const params = Object.fromEntries(
      Object.entries(rawParams).filter(([, value]) => value !== '' && value !== null && value !== undefined)
    );

    return this.apiService.get<CustomerListResponse>(this.endpoint, params).pipe(
      map(response => Array.isArray(response) ? response : response.items)
    );
  }

  getCustomer(id: number): Observable<Customer> {
    return this.apiService.get<Customer>(`${this.endpoint}/${id}`);
  }

  createCustomer(customer: Partial<Customer>): Observable<Customer> {
    return this.apiService.post<Customer>(this.endpoint, customer);
  }

  updateCustomer(id: number, customer: Partial<Customer>): Observable<Customer> {
    return this.apiService.put<Customer>(`${this.endpoint}/${id}`, customer);
  }

  deleteCustomer(id: number): Observable<any> {
    return this.apiService.delete(`${this.endpoint}/${id}`);
  }

  getCustomerOrders(id: number): Observable<any[]> {
    return this.apiService.get<any[]>(`${this.endpoint}/${id}/orders`);
  }
}

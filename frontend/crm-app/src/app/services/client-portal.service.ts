import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface PortalCustomer {
  id: number;
  first_name: string;
  last_name: string;
  phone: string;
  email?: string;
}

export interface PortalAuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  customer: PortalCustomer;
}

export interface PortalOrder {
  id: number;
  order_number: string;
  status: string;
  status_display: string;
  priority: string;
  device_title: string;
  problem_description: string;
  diagnosis?: string;
  work_description?: string;
  cost_estimate: number;
  final_cost?: number;
  remaining_payment: number;
  created_at: string;
  updated_at: string;
  estimated_completion?: string;
}

export interface PortalOrderCreate {
  device_type: string;
  brand: string;
  model_name: string;
  problem_description: string;
  serial_number?: string;
  imei?: string;
  color?: string;
  storage_capacity?: string;
  accessories?: string;
  device_condition?: string;
  cost_estimate: number;
}

@Injectable({
  providedIn: 'root'
})
export class ClientPortalService {
  private readonly baseUrl = `${environment.apiUrl}/portal`;
  private customerSubject = new BehaviorSubject<PortalCustomer | null>(null);

  customer$ = this.customerSubject.asObservable();

  constructor(private http: HttpClient) {
    const savedCustomer = localStorage.getItem('portal_customer');
    if (savedCustomer) {
      this.customerSubject.next(JSON.parse(savedCustomer));
    }
  }

  register(data: Record<string, unknown>): Observable<PortalAuthResponse> {
    return this.http.post<PortalAuthResponse>(`${this.baseUrl}/auth/register`, data).pipe(
      tap(response => this.saveSession(response))
    );
  }

  login(data: { phone: string; password: string }): Observable<PortalAuthResponse> {
    return this.http.post<PortalAuthResponse>(`${this.baseUrl}/auth/login`, data).pipe(
      tap(response => this.saveSession(response))
    );
  }

  logout(): void {
    localStorage.removeItem('portal_access_token');
    localStorage.removeItem('portal_customer');
    this.customerSubject.next(null);
  }

  me(): Observable<PortalCustomer> {
    return this.http.get<PortalCustomer>(`${this.baseUrl}/me`, {
      headers: this.portalHeaders()
    }).pipe(
      tap(customer => {
        localStorage.setItem('portal_customer', JSON.stringify(customer));
        this.customerSubject.next(customer);
      })
    );
  }

  orders(): Observable<PortalOrder[]> {
    return this.http.get<PortalOrder[]>(`${this.baseUrl}/orders`, {
      headers: this.portalHeaders()
    });
  }

  createOrder(data: PortalOrderCreate): Observable<PortalOrder> {
    return this.http.post<PortalOrder>(`${this.baseUrl}/orders`, data, {
      headers: this.portalHeaders()
    });
  }

  isAuthenticated(): boolean {
    return Boolean(localStorage.getItem('portal_access_token'));
  }

  private saveSession(response: PortalAuthResponse): void {
    localStorage.setItem('portal_access_token', response.access_token);
    localStorage.setItem('portal_customer', JSON.stringify(response.customer));
    this.customerSubject.next(response.customer);
  }

  private portalHeaders(): HttpHeaders {
    const token = localStorage.getItem('portal_access_token');
    let headers = new HttpHeaders({ 'Content-Type': 'application/json' });
    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }
    return headers;
  }
}

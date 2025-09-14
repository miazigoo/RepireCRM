import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { ApiService } from './api.service';
import { User, LoginRequest, LoginResponse, Shop } from '../core/models/models';
import { Router } from '@angular/router';
import { jwtDecode } from 'jwt-decode';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  private currentShopSubject = new BehaviorSubject<Shop | null>(null);

  public currentUser$ = this.currentUserSubject.asObservable();
  public currentShop$ = this.currentShopSubject.asObservable();

  constructor(
    private apiService: ApiService,
    private router: Router
  ) {
    this.initializeAuth();
  }

  private initializeAuth(): void {
    const token = localStorage.getItem('access_token');
    if (token && !this.isTokenExpired(token)) {
      this.getCurrentUser().subscribe();
    }
  }

  login(credentials: LoginRequest): Observable<LoginResponse> {
    return this.apiService.post<LoginResponse>('/auth/login', credentials)
      .pipe(
        tap(response => {
          localStorage.setItem('access_token', response.access_token);
          this.currentUserSubject.next(response.user);
          
          if (response.user.current_shop) {
            this.currentShopSubject.next(response.user.current_shop);
            localStorage.setItem('current_shop_id', response.user.current_shop.id.toString());
          }
        })
      );
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_shop_id');
    this.currentUserSubject.next(null);
    this.currentShopSubject.next(null);
    this.router.navigate(['/login']);
  }

  getCurrentUser(): Observable<User> {
    return this.apiService.get<User>('/auth/me')
      .pipe(
        tap(user => {
          this.currentUserSubject.next(user);
          if (user.current_shop) {
            this.currentShopSubject.next(user.current_shop);
            localStorage.setItem('current_shop_id', user.current_shop.id.toString());
          }
        })
      );
  }

  switchShop(shopId: number): Observable<any> {
    return this.apiService.post(`/auth/switch-shop/${shopId}`, {})
      .pipe(
        tap(() => {
          localStorage.setItem('current_shop_id', shopId.toString());
          this.getCurrentUser().subscribe();
        })
      );
  }

  isAuthenticated(): boolean {
    const token = localStorage.getItem('access_token');
    return token !== null && !this.isTokenExpired(token);
  }

  private isTokenExpired(token: string): boolean {
    try {
      const decoded: any = jwtDecode(token);
      const currentTime = Date.now() / 1000;
      return decoded.exp < currentTime;
    } catch {
      return true;
    }
  }

  get currentUser(): User | null {
    return this.currentUserSubject.value;
  }

  get currentShop(): Shop | null {
    return this.currentShopSubject.value;
  }
}
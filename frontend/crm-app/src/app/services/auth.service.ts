import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { ApiService } from './api.service';
import { User, LoginRequest, LoginResponse, Shop } from '../core/models/models';
import { Router } from '@angular/router';
import { jwtDecode } from 'jwt-decode';
import { authStorage } from '../core/utils/auth-storage';

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
  confirm_password: string;
}

export interface MessageResponse {
  message: string;
  success?: boolean;
}

export interface ProfileUpdateRequest {
  first_name?: string;
  last_name?: string;
  middle_name?: string;
  email?: string;
  phone?: string;
  profile_status?: string;
  bio?: string;
}

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
    const token = authStorage.getToken();
    if (!token || this.isTokenExpired(token)) {
      authStorage.clearAuth();
    }
  }

  login(credentials: LoginRequest): Observable<LoginResponse> {
    const normalizedCredentials: LoginRequest = {
      username: credentials.username.trim(),
      password: credentials.password.trim()
    };

    return this.apiService.post<LoginResponse>('/auth/login', normalizedCredentials)
      .pipe(
        tap(response => {
          authStorage.setToken(response.access_token);
          this.currentUserSubject.next(response.user);

          if (response.user.current_shop) {
            this.currentShopSubject.next(response.user.current_shop);
            authStorage.setCurrentShopId(response.user.current_shop.id);
          }
        })
      );
  }

  logout(): void {
    authStorage.clearAuth();
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
            authStorage.setCurrentShopId(user.current_shop.id);
          }
        })
      );
  }

  switchShop(shopId: number): Observable<User> {
    return this.apiService.post<User>(`/auth/switch-shop/${shopId}`, {})
      .pipe(
        tap(user => {
          this.currentUserSubject.next(user);
          if (user.current_shop) {
            this.currentShopSubject.next(user.current_shop);
            authStorage.setCurrentShopId(user.current_shop.id);
          }
        })
      );
  }

  changePassword(payload: ChangePasswordRequest): Observable<MessageResponse> {
    return this.apiService.post<MessageResponse>('/auth/change-password', payload);
  }

  getAvailableShops(): Observable<Shop[]> {
    return this.apiService.get<Shop[]>('/auth/shops');
  }

  updateProfile(payload: ProfileUpdateRequest): Observable<User> {
    return this.apiService.put<User>('/auth/profile', payload).pipe(
      tap(user => {
        this.currentUserSubject.next(user);
        if (user.current_shop) {
          this.currentShopSubject.next(user.current_shop);
        }
      })
    );
  }

  updateAvatar(file: File): Observable<User> {
    const formData = new FormData();
    formData.append('avatar', file);
    return this.apiService.postForm<User>('/auth/profile/avatar', formData).pipe(
      tap(user => this.currentUserSubject.next(user))
    );
  }

  getProfileStatistics(params?: Record<string, unknown>): Observable<any> {
    return this.apiService.get<any>('/auth/profile/statistics', params);
  }

  isAuthenticated(): boolean {
    const token = authStorage.getToken();
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

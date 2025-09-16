import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, delay, throwError } from 'rxjs';
import { User, LoginRequest, LoginResponse, Shop } from '../core/models/models';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class MockAuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  private currentShopSubject = new BehaviorSubject<Shop | null>(null);

  public currentUser$ = this.currentUserSubject.asObservable();
  public currentShop$ = this.currentShopSubject.asObservable();

  constructor(private router: Router) {}

  login(credentials: LoginRequest): Observable<LoginResponse> {
    if (credentials.username === 'admin' && credentials.password === 'admin123') {
      const mockUser: User = {
        id: 1,
        username: 'admin',
        first_name: 'Админ',
        last_name: 'Администратор',
        email: 'admin@repair-crm.com',
        is_director: true,
        is_active: true,
        current_shop: {
          id: 1,
          name: 'Ремонт+ Москва Центр',
          code: 'MSK01',
          is_active: true,
          timezone: 'Europe/Moscow',
          currency: 'RUB'
        },
        role: {
          id: 1,
          name: 'Администратор',
          code: 'admin'
        }
      };

      const response: LoginResponse = {
        access_token: 'mock-token-12345',
        token_type: 'Bearer',
        expires_in: 3600,
        user: mockUser
      };

      localStorage.setItem('access_token', response.access_token);
      this.currentUserSubject.next(mockUser);
      this.currentShopSubject.next(mockUser.current_shop!);

      return of(response).pipe(delay(1000));
    } else {
      // было: throw new Error(...)
      return throwError(() => new Error('Неверные учетные данные'));
    }
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_shop_id');
    this.currentUserSubject.next(null);
    this.currentShopSubject.next(null);
    this.router.navigate(['/login']);
  }

  getCurrentUser(): Observable<User> {
    const token = localStorage.getItem('access_token');
    if (!token) {
      // было: throw new Error('No token');
      return throwError(() => new Error('No token'));
    }

    const mockUser: User = {
      id: 1,
      username: 'admin',
      first_name: 'Админ',
      last_name: 'Администратор',
      email: 'admin@repair-crm.com',
      is_director: true,
      is_active: true,
      current_shop: {
        id: 1,
        name: 'Ремонт+ Москва Центр',
        code: 'MSK01',
        is_active: true,
        timezone: 'Europe/Moscow',
        currency: 'RUB'
      },
      role: {
        id: 1,
        name: 'Администратор',
        code: 'admin'
      }
    };

    this.currentUserSubject.next(mockUser);
    this.currentShopSubject.next(mockUser.current_shop!);

    return of(mockUser).pipe(delay(500));
  }

  switchShop(shopId: number): Observable<any> {
    return of({ success: true }).pipe(delay(500));
  }

  isAuthenticated(): boolean {
    const token = localStorage.getItem('access_token');
    return token !== null;
  }

  get currentUser(): User | null {
    return this.currentUserSubject.value;
  }

  get currentShop(): Shop | null {
    return this.currentShopSubject.value;
  }
}

import { Injectable } from '@angular/core';
import {
  HttpEvent, HttpHandler, HttpInterceptor, HttpRequest, HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';
import { authStorage, setSafeSessionItem } from '../utils/auth-storage';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private router: Router) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const token = authStorage.getToken();
    const currentShopId = authStorage.getCurrentShopId();
    const headers: Record<string, string> = {};

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (currentShopId) {
      headers['X-Current-Shop'] = currentShopId;
    }

    const authReq = Object.keys(headers).length
      ? req.clone({ setHeaders: headers })
      : req;

    return next.handle(authReq).pipe(
      catchError((err: HttpErrorResponse) => {
        if (err.status === 401 && !this.isLoginRequest(req)) {
          this.clearPrimarySession();
        }
        if (err.status === 402) {
          setSafeSessionItem(
            'repaircrm.subscriptionBlockMessage',
            this.extractErrorMessage(err),
          );
          this.router.navigate(['/admin/service']);
        }
        return throwError(() => err);
      })
    );
  }

  private clearPrimarySession(): void {
    authStorage.clearAuth();
    this.router.navigate(['/login']);
  }

  private isLoginRequest(request: HttpRequest<any>): boolean {
    return request.url.includes('/auth/login');
  }

  private extractErrorMessage(error: HttpErrorResponse): string {
    return (
      error.error?.error ||
      error.error?.detail ||
      error.error?.message ||
      'Доступ ограничен подпиской RepireCRM'
    );
  }
}

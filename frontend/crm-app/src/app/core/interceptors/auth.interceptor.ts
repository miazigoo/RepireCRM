import { Injectable } from '@angular/core';
import {
  HttpEvent, HttpHandler, HttpInterceptor, HttpRequest, HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private router: Router) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const token = localStorage.getItem('access_token');
    const currentShopId = localStorage.getItem('current_shop_id');
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
        if (err.status === 401) {
          this.clearPrimarySession();
        }
        return throwError(() => err);
      })
    );
  }

  private clearPrimarySession(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_shop_id');
    this.router.navigate(['/login']);
  }
}

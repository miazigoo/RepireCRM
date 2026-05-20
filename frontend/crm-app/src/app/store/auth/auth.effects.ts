import { Injectable, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { TimeoutError, of, timeout } from 'rxjs';
import { map, mergeMap, catchError, tap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import * as AuthActions from './auth.actions';
import { buildAuthRedirectUrl } from '../../core/utils/auth-storage';

const AUTH_REQUEST_TIMEOUT_MS = 10000;

function readBackendMessage(payload: unknown): string | null {
  if (!payload) {
    return null;
  }

  if (typeof payload === 'string') {
    const message = payload.trim();
    return message && !message.startsWith('<') ? message : null;
  }

  if (typeof payload !== 'object') {
    return null;
  }

  const data = payload as Record<string, unknown>;
  const candidates = [
    data['detail'],
    data['error'],
    data['message'],
    data['non_field_errors']
  ];

  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim()) {
      return candidate.trim();
    }

    if (Array.isArray(candidate) && candidate.length) {
      return candidate.filter(item => typeof item === 'string').join(' ').trim() || null;
    }
  }

  return null;
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (
    error instanceof TimeoutError ||
    (error as { name?: string })?.name === 'TimeoutError'
  ) {
    return 'Сервер не ответил за 10 секунд. Проверьте, что backend запущен и доступен.';
  }

  if (error instanceof HttpErrorResponse) {
    const backendMessage = readBackendMessage(error.error);

    if (error.status === 0) {
      return 'Сервер недоступен. Проверьте, что backend запущен и API доступен.';
    }

    if (error.status === 401) {
      return backendMessage || 'Неверный логин или пароль.';
    }

    if (error.status === 403) {
      return backendMessage || 'У пользователя нет доступа к CRM.';
    }

    if (error.status === 404 && error.url?.includes('/api/auth/login')) {
      return 'API входа не найден. Проверьте адрес backend и proxy-настройки.';
    }

    if (error.status >= 500) {
      return backendMessage || 'Сервер временно недоступен. Попробуйте еще раз позже.';
    }

    return backendMessage || fallback;
  }

  return readBackendMessage(error) || fallback;
}

@Injectable()
export class AuthEffects {
  private actions$ = inject(Actions);
  private authService = inject(AuthService);
  private router = inject(Router);

  login$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.login),
      mergeMap(({ credentials }) =>
        this.authService.login(credentials).pipe(
          timeout({ first: AUTH_REQUEST_TIMEOUT_MS }),
          tap(response => this.navigateAfterLogin(
            response.access_token,
            response.user.current_shop?.id
          )),
          map(response =>
            AuthActions.loginSuccess({
              user: response.user,
              currentShop: response.user.current_shop
            })
          ),
          catchError(error =>
            of(
              AuthActions.loginFailure({
                error: extractErrorMessage(error, 'Ошибка входа')
              })
            )
          )
        )
      )
    )
  );

  getCurrentUser$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.getCurrentUser),
      mergeMap(() =>
        this.authService.getCurrentUser().pipe(
          timeout({ first: AUTH_REQUEST_TIMEOUT_MS }),
          map(user => AuthActions.getCurrentUserSuccess({ user })),
          // При 401/ошибке — выходим из сессии
          catchError(() => of(AuthActions.logout()))
        )
      )
    )
  );

  logout$ = createEffect(
    () =>
      this.actions$.pipe(
        ofType(AuthActions.logout),
        tap(() => {
          // Навигация уже внутри AuthService.logout()
          this.authService.logout();
        })
      ),
    { dispatch: false }
  );

  switchShop$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.switchShop),
      mergeMap(({ shopId }) =>
        this.authService.switchShop(shopId).pipe(
          timeout({ first: AUTH_REQUEST_TIMEOUT_MS }),
          map(user =>
            AuthActions.switchShopSuccess({
              user,
              shop: user.current_shop!
            })
          ),
          catchError(error =>
            of(
              AuthActions.loginFailure({
                error: extractErrorMessage(error, 'Ошибка переключения магазина')
              })
            )
          )
        )
      )
    )
  );

  reloadAfterSwitchShop$ = createEffect(
    () =>
      this.actions$.pipe(
        ofType(AuthActions.switchShopSuccess),
        tap(() => {
          // Филиал влияет почти на все рабочие таблицы; reload убирает stale data.
          window.location.reload();
        })
      ),
    { dispatch: false }
  );

  private navigateAfterLogin(token?: string, shopId?: number): void {
    const targetUrl = buildAuthRedirectUrl('/dashboard', token, shopId);

    if (typeof window !== 'undefined') {
      window.location.replace(targetUrl);
      return;
    }

    void this.router.navigateByUrl(targetUrl, { replaceUrl: true }).catch(error => {
      console.error('Login navigation failed:', error);
    });
  }
}

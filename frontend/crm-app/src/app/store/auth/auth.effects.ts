import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { of } from 'rxjs';
import { map, mergeMap, catchError, tap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import * as AuthActions from './auth.actions';

function extractErrorMessage(error: any, fallback: string) {
  // Типичные поля ошибок у Django/DRF: error.detail, error.error, message
  return (
    error?.error?.detail ||
    error?.error?.error ||
    error?.message ||
    fallback
  );
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

  loginSuccess$ = createEffect(
    () =>
      this.actions$.pipe(
        ofType(AuthActions.loginSuccess),
        tap(() => this.router.navigate(['/dashboard']))
      ),
    { dispatch: false }
  );

  getCurrentUser$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.getCurrentUser),
      mergeMap(() =>
        this.authService.getCurrentUser().pipe(
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
          mergeMap(() =>
            this.authService.getCurrentUser().pipe(
              map(user =>
                AuthActions.switchShopSuccess({
                  shop: user.current_shop!
                })
              )
            )
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
}

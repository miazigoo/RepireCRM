import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { of } from 'rxjs';
import { map, mergeMap, catchError, tap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import * as AuthActions from './auth.actions';

@Injectable()
export class AuthEffects {
  login$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.login),
      mergeMap(({ credentials }) =>
        this.authService.login(credentials).pipe(
          map(response => AuthActions.loginSuccess({
            user: response.user,
            currentShop: response.user.current_shop
          })),
          catchError(error => of(AuthActions.loginFailure({
            error: error.error?.error || 'Ошибка входа'
          })))
        )
      )
    )
  );

  loginSuccess$ = createEffect(() =>
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
          catchError(() => of(AuthActions.logout()))
        )
      )
    )
  );

  logout$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.logout),
      tap(() => {
        this.authService.logout();
        this.router.navigate(['/login']);
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
              map(user => AuthActions.switchShopSuccess({
                shop: user.current_shop!
              }))
            )
          ),
          catchError(error => of(AuthActions.loginFailure({
            error: error.error?.error || 'Ошибка переключения магазина'
          })))
        )
      )
    )
  );

  constructor(
    private actions$: Actions,
    private authService: AuthService,
    private router: Router
  ) {}
}
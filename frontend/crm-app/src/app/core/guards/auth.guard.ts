import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { Observable, combineLatest, of } from 'rxjs';
import { map, filter, take } from 'rxjs/operators';
import { Store } from '@ngrx/store';
import { AppState } from '../../store/app.state';
import { selectIsAuthenticated, selectAuthLoading } from '../../store/auth/auth.selectors';
import * as AuthActions from '../../store/auth/auth.actions';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  constructor(
    private store: Store<AppState>,
    private router: Router
  ) {}

  canActivate(): Observable<boolean> {
    const token = localStorage.getItem('access_token');

    if (!token) {
      this.router.navigate(['/login']);
      return of(false);
    }

    // Запрашиваем пользователя (идемпотентно)
    this.store.dispatch(AuthActions.getCurrentUser());

    return combineLatest([
      this.store.select(selectIsAuthenticated),
      this.store.select(selectAuthLoading)
    ]).pipe(
      // ждём, пока закончится загрузка
      filter(([_, loading]) => loading === false),
      take(1),
      map(([isAuthenticated]) => {
        if (!isAuthenticated) {
          this.router.navigate(['/login']);
          return false;
        }
        return true;
      })
    );
  }
}

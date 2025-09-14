import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { Observable, map, take } from 'rxjs';
import { Store } from '@ngrx/store';
import { AppState } from '../../store/app.state';
import * as AuthActions from '../../store/auth/auth.actions';
import { selectIsAuthenticated } from '../../store/auth/auth.selectors';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  constructor(
    private store: Store<AppState>,
    private router: Router
  ) {}

  canActivate(): Observable<boolean> {
    // Проверяем аутентификацию при загрузке приложения
    this.store.dispatch(AuthActions.getCurrentUser());

    return this.store.select(selectIsAuthenticated).pipe(
      take(1),
      map(isAuthenticated => {
        if (!isAuthenticated) {
          this.router.navigate(['/login']);
          return false;
        }
        return true;
      })
    );
  }
}
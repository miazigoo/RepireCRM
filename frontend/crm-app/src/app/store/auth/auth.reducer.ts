import { createReducer, on } from '@ngrx/store';
import { initialAuthState } from './auth.state';
import * as AuthActions from './auth.actions';

export const authReducer = createReducer(
  initialAuthState,

  on(AuthActions.login, state => ({
    ...state,
    isLoading: true,
    error: null
  })),

  on(AuthActions.loginSuccess, (state, { user, currentShop }) => ({
    ...state,
    user,
    currentShop: currentShop || null,
    isLoading: false,
    error: null,
    isAuthenticated: true
  })),

  on(AuthActions.loginFailure, (state, { error }) => ({
    ...state,
    isLoading: false,
    error,
    isAuthenticated: false
  })),

  on(AuthActions.logout, () => initialAuthState),

  on(AuthActions.getCurrentUser, state => ({
    ...state,
    isLoading: true
  })),

  on(AuthActions.getCurrentUserSuccess, (state, { user }) => ({
    ...state,
    user,
    currentShop: user.current_shop || null,
    isLoading: false,
    isAuthenticated: true
  })),

  on(AuthActions.switchShopSuccess, (state, { shop }) => ({
    ...state,
    currentShop: shop
  }))
);
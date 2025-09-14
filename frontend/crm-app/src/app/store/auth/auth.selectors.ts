import { createFeatureSelector, createSelector } from '@ngrx/store';
import { AuthState } from './auth.state';

export const selectAuthState = createFeatureSelector<AuthState>('auth');

export const selectCurrentUser = createSelector(
  selectAuthState,
  state => state.user
);

export const selectCurrentShop = createSelector(
  selectAuthState,
  state => state.currentShop
);

export const selectIsAuthenticated = createSelector(
  selectAuthState,
  state => state.isAuthenticated
);

export const selectAuthLoading = createSelector(
  selectAuthState,
  state => state.isLoading
);

export const selectAuthError = createSelector(
  selectAuthState,
  state => state.error
);
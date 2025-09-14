import { createAction, props } from '@ngrx/store';
import { User, LoginRequest, Shop } from '../../core/models/models';

export const login = createAction(
  '[Auth] Login',
  props<{ credentials: LoginRequest }>()
);

export const loginSuccess = createAction(
  '[Auth] Login Success',
  props<{ user: User; currentShop?: Shop }>()
);

export const loginFailure = createAction(
  '[Auth] Login Failure',
  props<{ error: string }>()
);

export const logout = createAction('[Auth] Logout');

export const getCurrentUser = createAction('[Auth] Get Current User');

export const getCurrentUserSuccess = createAction(
  '[Auth] Get Current User Success',
  props<{ user: User }>()
);

export const switchShop = createAction(
  '[Auth] Switch Shop',
  props<{ shopId: number }>()
);

export const switchShopSuccess = createAction(
  '[Auth] Switch Shop Success',
  props<{ shop: Shop }>()
);
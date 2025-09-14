import { User, Shop } from '../../core/models/models';

export interface AuthState {
  user: User | null;
  currentShop: Shop | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
}

export const initialAuthState: AuthState = {
  user: null,
  currentShop: null,
  isLoading: false,
  error: null,
  isAuthenticated: false
};
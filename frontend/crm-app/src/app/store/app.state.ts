import { AuthState } from './auth/auth.state';
import { CustomersState } from './customers/customers.state';
import { OrdersState } from './orders/orders.state';

export interface AppState {
  auth: AuthState;
  customers: CustomersState;
  orders: OrdersState;
}
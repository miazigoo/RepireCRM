export interface OrdersState {
  orders: any[];
  loading: boolean;
  error: string | null;
}

export const initialOrdersState: OrdersState = {
  orders: [],
  loading: false,
  error: null
};

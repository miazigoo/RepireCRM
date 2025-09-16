export interface CustomersState {
  customers: any[];
  loading: boolean;
  error: string | null;
}

export const initialCustomersState: CustomersState = {
  customers: [],
  loading: false,
  error: null
};

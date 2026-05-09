import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export type OnlinePaymentMethodType = 'any' | 'bank_card' | 'sbp' | 'yoo_money';

export interface OnlinePayment {
  id: number;
  provider: string;
  purpose: 'order' | 'subscription';
  status: 'pending' | 'waiting_for_capture' | 'succeeded' | 'canceled' | 'failed';
  payment_method_type: OnlinePaymentMethodType;
  amount: number;
  currency: string;
  confirmation_url: string;
  provider_payment_id: string;
  is_test: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class PaymentsService {
  constructor(private apiService: ApiService) {}

  createOrderPayment(
    orderId: number,
    paymentMethodType: OnlinePaymentMethodType,
    amount?: number,
  ): Observable<OnlinePayment> {
    return this.apiService.post<OnlinePayment>(`/finance/order/${orderId}/online-payment`, {
      amount,
      payment_method_type: paymentMethodType,
    });
  }

  syncPayment(paymentId: number): Observable<OnlinePayment> {
    return this.apiService.post<OnlinePayment>(`/finance/online-payments/${paymentId}/sync`, {});
  }
}

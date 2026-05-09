import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from './api.service';
import { OnlinePayment, PaymentsService } from './payments.service';

describe('PaymentsService', () => {
  let service: PaymentsService;
  let apiService: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    apiService = jasmine.createSpyObj<ApiService>('ApiService', ['post']);

    TestBed.configureTestingModule({
      providers: [PaymentsService, { provide: ApiService, useValue: apiService }],
    });

    service = TestBed.inject(PaymentsService);
  });

  it('creates order online payment with selected method and amount', () => {
    const payment = {
      id: 9,
      provider: 'yookassa',
      purpose: 'order',
      status: 'pending',
      payment_method_type: 'bank_card',
      amount: 4500,
      currency: 'RUB',
      confirmation_url: 'http://127.0.0.1:8030/api/finance/online-payments/9/test-checkout',
      provider_payment_id: 'test_9',
      is_test: true,
    } as OnlinePayment;
    apiService.post.and.returnValue(of(payment));

    service.createOrderPayment(7, 'bank_card', 4500).subscribe((result) => {
      expect(result).toEqual(payment);
    });

    expect(apiService.post).toHaveBeenCalledOnceWith('/finance/order/7/online-payment', {
      amount: 4500,
      payment_method_type: 'bank_card',
    });
  });
});

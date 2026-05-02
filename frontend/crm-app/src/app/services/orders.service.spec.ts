import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { Order, RepairStage } from '../core/models/models';
import { ApiService } from './api.service';
import { OrdersService } from './orders.service';

describe('OrdersService', () => {
  let service: OrdersService;
  let apiService: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    apiService = jasmine.createSpyObj<ApiService>('ApiService', [
      'get',
      'post',
      'put',
      'postForm',
    ]);

    TestBed.configureTestingModule({
      providers: [
        OrdersService,
        { provide: ApiService, useValue: apiService },
      ],
    });

    service = TestBed.inject(OrdersService);
  });

  it('fetches paginated orders with filters', () => {
    const orders = [
      { id: 1, order_number: 'ORD-001', status: 'received' },
    ] as Order[];
    apiService.get.and.returnValue(of(orders));

    service.getOrders(2, 10, { status: 'ready', search: 'iphone' }).subscribe((result) => {
      expect(result).toEqual(orders);
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/orders', {
      page: 2,
      page_size: 10,
      status: 'ready',
      search: 'iphone',
    });
  });

  it('posts repair stages as multipart form data', () => {
    const formData = new FormData();
    formData.append('title', 'Перепаяли Type-C');
    const stage = { id: 7, title: 'Перепаяли Type-C' } as RepairStage;
    apiService.postForm.and.returnValue(of(stage));

    service.addRepairStage(42, formData).subscribe((result) => {
      expect(result).toEqual(stage);
    });

    expect(apiService.postForm).toHaveBeenCalledOnceWith('/orders/42/repair-stages', formData);
  });

  it('requests customer approval with amount and description', () => {
    apiService.post.and.returnValue(of({ id: 3 }));

    service
      .requestApproval(42, {
        title: 'Замена дисплея',
        description: 'Оригинальный модуль',
        amount: 12000,
      })
      .subscribe();

    expect(apiService.post).toHaveBeenCalledOnceWith('/orders/42/approvals', {
      title: 'Замена дисплея',
      description: 'Оригинальный модуль',
      amount: 12000,
    });
  });
});

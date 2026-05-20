import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { DeviceModel, Order, RepairStage } from '../core/models/models';
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
      'delete',
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

    expect(apiService.get).toHaveBeenCalledOnceWith('/orders/', {
      page: 2,
      page_size: 10,
      status: 'ready',
      search: 'iphone',
    });
  });

  it('omits empty filter values before calling the orders API', () => {
    apiService.get.and.returnValue(of([]));

    service.getOrders(1, 100, { search: '', status: '' as any, priority: '' as any }).subscribe();

    expect(apiService.get).toHaveBeenCalledOnceWith('/orders/', {
      page: 1,
      page_size: 100,
    });
  });

  it('unwraps backend paginated order responses', () => {
    const order = { id: 1, order_number: 'ORD-001', status: 'received' } as Order;
    apiService.get.and.returnValue(of({ items: [order], count: 1 }));

    service.getOrders().subscribe((result) => {
      expect(result).toEqual([order]);
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

  it('updates order status with an optional status comment', () => {
    const order = { id: 42, order_number: 'ORD-042', status: 'ready' } as Order;
    apiService.put.and.returnValue(of(order));

    service.updateOrder(42, {
      status: 'ready',
      status_comment: 'Изменено из карточки заказа',
    }).subscribe((result) => {
      expect(result).toEqual(order);
    });

    expect(apiService.put).toHaveBeenCalledOnceWith('/orders/42', {
      status: 'ready',
      status_comment: 'Изменено из карточки заказа',
    });
  });

  it('creates orders using trailing slash endpoint to avoid Django POST redirect', () => {
    const order = { id: 8, order_number: 'ORD-008' } as Order;
    const payload = { customer_id: 1, device: { model_id: 2 } };
    apiService.post.and.returnValue(of(order));

    service.createOrder(payload).subscribe((result) => {
      expect(result).toEqual(order);
    });

    expect(apiService.post).toHaveBeenCalledOnceWith('/orders/', payload);
  });

  it('loads device models for order creation', () => {
    const models = [
      {
        id: 2,
        name: 'iPhone 15 Pro',
        brand: { id: 1, name: 'Apple' },
        device_type: { id: 1, name: 'Смартфон' },
      },
    ] as DeviceModel[];
    apiService.get.and.returnValue(of(models));

    service.getDeviceModels().subscribe((result) => {
      expect(result).toEqual(models);
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/orders/device-models');
  });

  it('creates missing device models from order form', () => {
    const model = {
      id: 5,
      name: 'Galaxy A55',
      brand: { id: 1, name: 'Samsung' },
      device_type: { id: 1, name: 'Смартфон' },
    } as DeviceModel;
    const payload = {
      brand_name: 'Samsung',
      name: 'Galaxy A55',
      device_type_name: 'Смартфон',
    };
    apiService.post.and.returnValue(of(model));

    service.createDeviceModel(payload).subscribe((result) => {
      expect(result).toEqual(model);
    });

    expect(apiService.post).toHaveBeenCalledOnceWith('/orders/device-models', payload);
  });

  it('manages additional services through the orders catalog API', () => {
    const servicePayload = { name: 'Бронестекло', category: 'protection', price: 500 };
    apiService.post.and.returnValue(of({ id: 10, ...servicePayload }));
    apiService.put.and.returnValue(of({ id: 10, ...servicePayload, price: 600 }));
    apiService.delete.and.returnValue(of({ success: true }));

    service.createAdditionalService(servicePayload).subscribe();
    service.updateAdditionalService(10, { price: 600 }).subscribe();
    service.deleteAdditionalService(10).subscribe();

    expect(apiService.post).toHaveBeenCalledWith('/orders/additional-services', servicePayload);
    expect(apiService.put).toHaveBeenCalledWith('/orders/additional-services/10', { price: 600 });
    expect(apiService.delete).toHaveBeenCalledWith('/orders/additional-services/10');
  });

  it('can include inactive services for catalog management', () => {
    apiService.get.and.returnValue(of([]));

    service.getAdditionalServices(true).subscribe();

    expect(apiService.get).toHaveBeenCalledOnceWith('/orders/additional-services', {
      include_inactive: true,
    });
  });
});

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { Order } from '../../../core/models/models';
import { OrdersService } from '../../../services/orders.service';
import { PaymentsService } from '../../../services/payments.service';
import { OrderDetailComponent } from './order-detail.component';

describe('OrderDetailComponent', () => {
  let fixture: ComponentFixture<OrderDetailComponent>;
  let component: OrderDetailComponent;
  let ordersService: jasmine.SpyObj<OrdersService>;
  let paymentsService: jasmine.SpyObj<PaymentsService>;

  const order = {
    id: 2,
    order_number: 'ORD-SPB01-000002',
    status: 'received',
    priority: 'urgent',
    problem_description: 'Не включается',
    accessories: 'Коробка',
    cost_estimate: 900,
    total_cost: 1800,
    prepayment: 0,
    remaining_payment: 1800,
    created_at: '2026-05-05T20:32:00Z',
    updated_at: '2026-05-05T20:32:00Z',
    estimated_completion: '2026-05-23T00:00:00Z',
    additional_services: [
      {
        service: {
          id: 7,
          name: 'Защитное стекло',
          category: 'Аксессуары',
          price: 900,
        },
        quantity: 1,
        price: 900,
        total_price: 900,
      },
    ],
    customer: {
      id: 1,
      first_name: 'Петр',
      last_name: 'Петров',
      phone: '+79161234567',
      email: 'petrov@example.com',
      orders_count: 3,
      total_spent: 3300,
      created_at: '2026-05-01T10:00:00Z',
      updated_at: '2026-05-01T10:00:00Z',
    },
    device: {
      id: 1,
      color: 'Черный',
      storage_capacity: '128 ГБ',
      model: {
        id: 1,
        name: 'iPhone 13',
        brand: { id: 1, name: 'Apple' },
        device_type: { id: 1, name: 'Смартфон' },
      },
    },
  } as Order;

  beforeEach(async () => {
    ordersService = jasmine.createSpyObj<OrdersService>('OrdersService', [
      'getOrder',
      'getStatusHistory',
      'getRepairStages',
      'getApprovals',
      'getAuditLog',
      'updateOrder',
      'addRepairStage',
      'requestApproval',
    ]);
    ordersService.getOrder.and.returnValue(of(order));
    ordersService.getStatusHistory.and.returnValue(of([]));
    ordersService.getRepairStages.and.returnValue(of([]));
    ordersService.getApprovals.and.returnValue(of([]));
    ordersService.getAuditLog.and.returnValue(of([]));
    ordersService.updateOrder.and.callFake((_: number, payload: any) =>
      of({ ...order, ...payload } as Order),
    );
    paymentsService = jasmine.createSpyObj<PaymentsService>('PaymentsService', [
      'createOrderPayment',
    ]);
    paymentsService.createOrderPayment.and.returnValue(
      of({
        id: 12,
        provider: 'yookassa',
        purpose: 'order',
        status: 'pending',
        payment_method_type: 'sbp',
        amount: 1800,
        currency: 'RUB',
        confirmation_url: '',
        provider_payment_id: 'test_12',
        is_test: true,
      }),
    );

    await TestBed.configureTestingModule({
      imports: [OrderDetailComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: ActivatedRoute, useValue: { snapshot: { params: { id: 2 } } } },
        { provide: OrdersService, useValue: ordersService },
        { provide: PaymentsService, useValue: paymentsService },
        {
          provide: MatSnackBar,
          useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']),
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(OrderDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('renders the redesigned order detail page with visible rouble formatting', () => {
    const text = normalizeText(fixture.nativeElement);

    expect(text).toContain('Карточка заказа');
    expect(text).toContain('ORD-SPB01-000002');
    expect(text).toContain('Петров Петр');
    expect(text).toContain('900 ₽');
    expect(text).toContain('1 800 ₽');
    expect(text).not.toContain('RUB');
    expect(fixture.nativeElement.querySelector('.order-detail-page')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('mat-card')).toBeFalsy();
  });

  it('renders order status visuals as inline svg icons', () => {
    component.statusHistory = [
      {
        id: 1,
        old_status: 'ready',
        new_status: 'completed',
        changed_at: '2026-05-05T21:32:00Z',
        changed_by_name: 'Тест',
      },
    ];
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.order-avatar svg')).toBeTruthy();
    expect(fixture.nativeElement.querySelectorAll('.status-rail svg').length).toBe(8);
    expect(component.getStatusIconPaths('completed').length).toBeGreaterThan(0);
  });

  it('updates order status from the redesigned status rail', () => {
    component.setOrderStatus('ready');

    expect(ordersService.updateOrder).toHaveBeenCalledWith(2, {
      status: 'ready',
      status_comment: 'Изменено из карточки заказа',
    });
    expect(component.order?.status).toBe('ready');
    expect(ordersService.getStatusHistory).toHaveBeenCalledTimes(2);
  });

  it('requires the handover form before completing an order', () => {
    spyOn(component, 'openHandoverDialog').and.stub();

    component.setOrderStatus('completed');

    expect(component.handoverNeedsAttention).toBeTrue();
    expect(component.openHandoverDialog).toHaveBeenCalled();
    expect(ordersService.updateOrder).not.toHaveBeenCalled();
  });

  it('completes an order with final cost and prepayment from handover form', () => {
    component.handoverForm.patchValue({
      final_cost: 1200,
      prepayment: 200,
      status_comment: 'Оплата на кассе',
    });

    component.completeOrder();

    expect(ordersService.updateOrder).toHaveBeenCalledWith(2, {
      status: 'completed',
      final_cost: 1200,
      prepayment: 200,
      status_comment: 'Оплата на кассе',
    });
    expect(component.order?.status).toBe('completed');
    expect(component.handoverNeedsAttention).toBeFalse();
  });

  it('shows total and remaining payment with additional services included', () => {
    component.order = {
      ...order,
      cost_estimate: 2400,
      final_cost: 2400,
      total_cost: 3900,
      prepayment: 500,
      remaining_payment: 3400,
      additional_services: [
        {
          service: {
            id: 8,
            name: 'Быстрый чехол',
            category: 'Аксессуары',
            price: 1500,
          },
          quantity: 1,
          price: 1500,
          total_price: 1500,
        },
      ],
    } as Order;
    fixture.detectChanges();

    const text = normalizeText(fixture.nativeElement);

    expect(component.getOrderAmount(component.order)).toBe(3900);
    expect(component.getDisplayRemainingPayment(component.order)).toBe(3400);
    expect(text).toContain('3 900 ₽');
    expect(text).toContain('3 400 ₽');
    expect(text).toContain('Услуги');
  });

  it('creates online payment for remaining order amount', () => {
    component.startOnlinePayment('sbp');

    expect(paymentsService.createOrderPayment).toHaveBeenCalledOnceWith(2, 'sbp', 1800);
    expect(component.onlinePaymentLoading).toBeNull();
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});

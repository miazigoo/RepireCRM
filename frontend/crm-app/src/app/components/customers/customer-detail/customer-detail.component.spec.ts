import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { Customer } from '../../../core/models/models';
import { CustomersService } from '../../../services/customers.service';
import { CustomerDetailComponent } from './customer-detail.component';

describe('CustomerDetailComponent', () => {
  let fixture: ComponentFixture<CustomerDetailComponent>;
  let component: CustomerDetailComponent;
  let customersService: jasmine.SpyObj<CustomersService>;
  let router: Router;

  const customer = {
    id: 4,
    first_name: 'Петр',
    last_name: 'Петров',
    phone: '+79161234567',
    email: 'petrov@example.com',
    source: 'website',
    preferred_channel: 'email',
    marketing_consent: true,
    orders_count: 1,
    total_spent: 12500,
    created_at: '2026-05-01T10:00:00Z',
    updated_at: '2026-05-02T10:00:00Z',
  } as Customer;

  beforeEach(async () => {
    customersService = jasmine.createSpyObj<CustomersService>('CustomersService', [
      'getCustomer',
      'getCustomerOrders',
      'deleteCustomer',
    ]);
    customersService.getCustomer.and.returnValue(of(customer));
    customersService.getCustomerOrders.and.returnValue(of([
      {
        id: 12,
        order_number: 'ORD-001',
        status: 'ready',
        device: 'Apple iPhone 12',
        cost_estimate: 12500,
        final_cost: null,
        created_at: '2026-05-03T12:00:00Z',
        shop: 'Сервисный центр',
      },
    ]));

    await TestBed.configureTestingModule({
      imports: [CustomerDetailComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: ActivatedRoute, useValue: { snapshot: { params: { id: 4 } } } },
        { provide: CustomersService, useValue: customersService },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CustomerDetailComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('renders the redesigned customer detail page with rouble formatting', () => {
    const text = normalizeText(fixture.nativeElement);

    expect(text).toContain('Карточка клиента');
    expect(text).toContain('Петров Петр');
    expect(text).toContain('Заказы клиента');
    expect(text).toContain('12 500 ₽');
    expect(text).not.toContain('RUB');
    expect(fixture.nativeElement.querySelector('.customer-detail-page')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('mat-card')).toBeFalsy();
  });

  it('opens new order creation with the current customer id', () => {
    const navigate = spyOn(router, 'navigate');

    component.createOrder();

    expect(navigate).toHaveBeenCalledWith(['/orders/new'], {
      queryParams: { customer_id: 4 },
    });
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});

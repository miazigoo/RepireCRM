import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { Customer } from '../../../core/models/models';
import { CustomersService } from '../../../services/customers.service';
import { CustomersListComponent } from './customers-list.component';

describe('CustomersListComponent', () => {
  let fixture: ComponentFixture<CustomersListComponent>;
  let component: CustomersListComponent;
  let customersService: jasmine.SpyObj<CustomersService>;

  const customers = [
    {
      id: 1,
      first_name: 'Петр',
      last_name: 'Петров',
      phone: '+79161234567',
      email: 'petrov@example.com',
      source: 'website',
      orders_count: 3,
      total_spent: 3300,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 2,
      first_name: 'Анна',
      last_name: 'Иванова',
      phone: '+79000000000',
      source: 'referral',
      orders_count: 0,
      total_spent: 0,
      created_at: '2025-01-10T10:00:00Z',
      updated_at: '2025-01-10T10:00:00Z',
    },
  ] as Customer[];

  beforeEach(async () => {
    customersService = jasmine.createSpyObj<CustomersService>('CustomersService', [
      'getCustomers',
      'deleteCustomer',
    ]);
    customersService.getCustomers.and.returnValue(of(customers));

    await TestBed.configureTestingModule({
      imports: [CustomersListComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: CustomersService, useValue: customersService },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CustomersListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('renders the redesigned customers workspace with metrics and client cards', () => {
    const text = normalizeText(fixture.nativeElement);

    expect(text).toContain('Клиентская база');
    expect(text).toContain('Всего клиентов');
    expect(text).toContain('База клиентов');
    expect(text).toContain('Петров Петр');
    expect(text).toContain('3 300 ₽');
    expect(text).not.toContain('RUB');
  });

  it('calculates customer metrics for the current selection', () => {
    expect(component.totalCustomers).toBe(2);
    expect(component.customersWithOrders).toBe(1);
    expect(component.ordersTotal).toBe(3);
    expect(component.revenueTotal).toBe(3300);
    expect(component.averageSpent).toBe(3300);
    expect(component.topSourceLabel).toBe('Сайт');
  });

  it('reloads customers when filters change', fakeAsync(() => {
    customersService.getCustomers.calls.reset();

    component.filtersForm.patchValue({ search: 'Петр' });
    tick(300);

    expect(customersService.getCustomers).toHaveBeenCalledWith(
      1,
      100,
      jasmine.objectContaining({ search: 'Петр' })
    );
  }));

  it('resets filters to visible default values', () => {
    component.filtersForm.patchValue({ search: 'Анна', source: 'referral', has_orders: true });

    component.clearFilters();

    expect(component.filtersForm.getRawValue()).toEqual({
      search: '',
      source: '',
      has_orders: '',
      created_from: '',
      created_to: '',
    });
    expect(component.hasActiveFilters).toBeFalse();
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { Customer } from '../../../core/models/models';
import { CustomersService } from '../../../services/customers.service';
import { CustomerFormComponent } from './customer-form.component';

describe('CustomerFormComponent', () => {
  let fixture: ComponentFixture<CustomerFormComponent>;
  let component: CustomerFormComponent;
  let customersService: jasmine.SpyObj<CustomersService>;
  let router: Router;

  const createdCustomer = {
    id: 9,
    first_name: 'Анна',
    last_name: 'Иванова',
    phone: '+79990000000',
    orders_count: 0,
    total_spent: 0,
    marketing_consent: true,
    created_at: '2026-05-06T10:00:00Z',
    updated_at: '2026-05-06T10:00:00Z',
  } as Customer;

  beforeEach(async () => {
    customersService = jasmine.createSpyObj<CustomersService>('CustomersService', [
      'getCustomer',
      'createCustomer',
      'updateCustomer',
    ]);
    customersService.createCustomer.and.returnValue(of(createdCustomer));

    await TestBed.configureTestingModule({
      imports: [CustomerFormComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: ActivatedRoute, useValue: { params: of({}) } },
        { provide: CustomersService, useValue: customersService },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CustomerFormComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('renders the redesigned customer form without legacy card layout', () => {
    const text = normalizeText(fixture.nativeElement);

    expect(text).toContain('Клиентская база');
    expect(text).toContain('Профиль');
    expect(text).toContain('Контакты');
    expect(text).toContain('Готовность карточки');
    expect(fixture.nativeElement.querySelector('.customer-form-page')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('mat-card')).toBeFalsy();
  });

  it('trims values, formats birth date and creates a customer', () => {
    const navigate = spyOn(router, 'navigate');

    component.customerForm.patchValue({
      first_name: ' Анна ',
      last_name: ' Иванова ',
      phone: '+7 999 000-00-00',
      email: ' anna@example.com ',
      birth_date: new Date('1995-04-10T12:00:00Z'),
      source: 'referral',
      preferred_channel: 'sms',
      marketing_consent: true,
      notes: ' постоянный клиент ',
    });

    component.onSubmit();

    expect(customersService.createCustomer).toHaveBeenCalledWith(jasmine.objectContaining({
      first_name: 'Анна',
      last_name: 'Иванова',
      phone: '+7 999 000-00-00',
      email: 'anna@example.com',
      birth_date: '1995-04-10',
      marketing_consent: true,
      notes: 'постоянный клиент',
    }));
    expect(navigate).toHaveBeenCalledWith(['/customers', 9]);
  });

  it('updates an existing customer and allows clearing birth date', () => {
    const navigate = spyOn(router, 'navigate');
    customersService.updateCustomer.and.returnValue(of(createdCustomer));
    component.isEditMode = true;
    component.customerId = 9;
    component.customerForm.patchValue({
      first_name: ' Анна ',
      last_name: ' Иванова ',
      phone: '+7 999 000-00-00',
      email: '',
      birth_date: null,
      marketing_consent: false,
    });

    component.onSubmit();

    expect(customersService.updateCustomer).toHaveBeenCalledWith(9, jasmine.objectContaining({
      first_name: 'Анна',
      last_name: 'Иванова',
      birth_date: null,
      marketing_consent: false,
    }));
    expect(navigate).toHaveBeenCalledWith(['/customers', 9]);
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});

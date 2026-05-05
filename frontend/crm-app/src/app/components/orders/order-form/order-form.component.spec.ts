import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { Customer, DeviceModel } from '../../../core/models/models';
import { CustomersService } from '../../../services/customers.service';
import { OrdersService } from '../../../services/orders.service';
import { OrderFormComponent } from './order-form.component';

describe('OrderFormComponent', () => {
  let fixture: ComponentFixture<OrderFormComponent>;
  let component: OrderFormComponent;
  let ordersService: jasmine.SpyObj<OrdersService>;
  let customersService: jasmine.SpyObj<CustomersService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  const customer = {
    id: 1,
    first_name: 'Иван',
    last_name: 'Петров',
    phone: '+79991234567',
  } as Customer;

  const deviceModel = {
    id: 4,
    name: 'iPhone 15 Pro',
    brand: { id: 1, name: 'Apple' },
    device_type: { id: 1, name: 'Смартфон' },
  } as DeviceModel;

  beforeEach(async () => {
    ordersService = jasmine.createSpyObj<OrdersService>('OrdersService', [
      'getDeviceModels',
      'getAdditionalServices',
      'createDeviceModel',
      'createOrder',
      'updateOrder',
      'getOrder',
    ]);
    customersService = jasmine.createSpyObj<CustomersService>('CustomersService', [
      'getCustomers',
      'createCustomer',
    ]);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);

    ordersService.getDeviceModels.and.returnValue(of([deviceModel]));
    ordersService.getAdditionalServices.and.returnValue(
      of([
        {
          id: 10,
          name: 'Диагностика',
          category: 'Базовые',
          price: 1000,
        } as any,
      ])
    );
    customersService.getCustomers.and.returnValue(of([customer]));

    await TestBed.configureTestingModule({
      imports: [OrderFormComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: ActivatedRoute, useValue: { params: of({}) } },
        { provide: OrdersService, useValue: ordersService },
        { provide: CustomersService, useValue: customersService },
        { provide: MatSnackBar, useValue: snackBar },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(OrderFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('renders the redesigned intake shell with live summary and inline SVG panels', () => {
    const text = normalizeText(fixture.nativeElement);

    expect(text).toContain('Приемка в сервис');
    expect(text).toContain('Карточка приемки');
    expect(text).toContain('Быстро добавить');
    expect(fixture.nativeElement.querySelectorAll('.panel-icon svg').length).toBeGreaterThan(1);
  });

  it('creates a quick customer and moves to the next step', () => {
    const created = { ...customer, id: 7, first_name: 'Анна', last_name: 'Иванова' };
    customersService.createCustomer.and.returnValue(of(created));
    component.customerForm.get('newCustomer')?.patchValue({
      first_name: 'Анна',
      last_name: 'Иванова',
      phone: '+79990000000',
      email: '',
    });
    const stepper = { next: jasmine.createSpy('next') } as any;

    component.createCustomerAndContinue(stepper);

    expect(customersService.createCustomer).toHaveBeenCalledOnceWith({
      first_name: 'Анна',
      last_name: 'Иванова',
      phone: '+79990000000',
      email: undefined,
    });
    expect(component.selectedCustomer).toEqual(created);
    expect(stepper.next).toHaveBeenCalled();
  });

  it('creates a missing device model before moving to order details', () => {
    const createdModel = {
      ...deviceModel,
      id: 8,
      name: 'Galaxy A55',
      brand: { id: 2, name: 'Samsung' },
    } as DeviceModel;
    ordersService.createDeviceModel.and.returnValue(of(createdModel));
    component.deviceForm.patchValue({ model: 'Samsung Galaxy A55' });
    const stepper = { next: jasmine.createSpy('next') } as any;

    component.onDeviceStepNext(stepper);

    expect(ordersService.createDeviceModel).toHaveBeenCalledOnceWith({
      brand_name: 'Samsung',
      name: 'Galaxy A55',
      device_type_name: 'Смартфон',
    });
    expect(component.selectedDeviceModel).toEqual(createdModel);
    expect(stepper.next).toHaveBeenCalled();
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});

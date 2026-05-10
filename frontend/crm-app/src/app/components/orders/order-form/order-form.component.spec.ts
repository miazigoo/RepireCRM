import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
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
  let router: Router;

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
  const caseService = {
    id: 11,
    name: 'Чехол',
    category: 'Аксессуары',
    price: 1500,
  } as any;

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
        caseService,
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
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('renders the redesigned intake shell with live summary and inline SVG panels', () => {
    const text = normalizeText(fixture.nativeElement);

    expect(text).toContain('Приемка в сервис');
    expect(text).toContain('Карточка приемки');
    expect(text).toContain('Быстро добавить');
    expect(fixture.nativeElement.querySelectorAll('.panel-icon svg').length).toBeGreaterThan(1);
    expect(fixture.nativeElement.querySelectorAll('.summary-status-grid svg').length).toBe(3);
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

  it('shows model suggestions on click after the catalog loads', fakeAsync(() => {
    let latestSuggestions: DeviceModel[] = [];
    const redmiModel = {
      ...deviceModel,
      id: 12,
      name: 'Redmi 14C',
      brand: { id: 2, name: 'Xiaomi' },
    } as DeviceModel;

    component.deviceModels = [];
    component.deviceForm.get('model')?.setValue('');
    component.filteredDeviceModels.subscribe(models => latestSuggestions = models);

    expect(latestSuggestions).toEqual([]);

    component.deviceModels = [redmiModel];
    component.showDeviceModelSuggestions();
    tick();

    expect(latestSuggestions).toEqual([redmiModel]);
  }));

  it('does not reopen model suggestions after a concrete model is selected', fakeAsync(() => {
    let latestSuggestions: DeviceModel[] = [];
    const samsungModel = {
      ...deviceModel,
      id: 22,
      name: 'Galaxy S24',
      brand: { id: 2, name: 'Samsung' },
    } as DeviceModel;

    component.deviceModels = [samsungModel, deviceModel];
    component.filteredDeviceModels.subscribe(models => latestSuggestions = models);

    component.onDeviceModelSelected(samsungModel);
    component.showDeviceModelSuggestions();
    tick();

    expect(component.selectedDeviceModel).toEqual(samsungModel);
    expect(latestSuggestions).toEqual([]);
  }));

  it('keeps a broader set of frequent device chips', () => {
    component.deviceModels = Array.from({ length: 20 }, (_, index) => ({
      ...deviceModel,
      id: index + 1,
      name: `Модель ${index + 1}`,
    })) as DeviceModel[];

    expect(component.popularDeviceModels.length).toBe(12);
  });

  it('adds a quick case service once during order creation', () => {
    component.addQuickService('Чехол');
    component.addQuickService('Чехол');

    expect(component.selectedServices).toEqual([caseService]);
    expect(component.servicesTotal).toBe(1500);
    expect(component.isServiceSelected(caseService)).toBeTrue();
  });

  it('creates an order payload without an empty estimated completion date', () => {
    const navigate = spyOn(router, 'navigate');
    const createdOrder = { id: 55 } as any;
    ordersService.createOrder.and.returnValue(of(createdOrder));
    component.customerForm.patchValue({ customer });
    component.deviceForm.patchValue({ model: deviceModel, model_id: deviceModel.id });
    component.orderForm.patchValue({
      problem_description: 'Проверка payload',
      cost_estimate: 1900,
      estimated_completion: '',
    });
    component.addQuickService('Чехол');

    component.onSubmit();

    const payload = ordersService.createOrder.calls.mostRecent().args[0];
    expect(payload.estimated_completion).toBeUndefined();
    expect(payload.additional_services).toEqual([{ service_id: 11, quantity: 1 }]);
    expect(navigate).toHaveBeenCalledWith(['/orders', 55]);
  });

  function normalizeText(element: HTMLElement): string {
    return element.textContent?.replace(/\s+/g, ' ').trim() || '';
  }
});

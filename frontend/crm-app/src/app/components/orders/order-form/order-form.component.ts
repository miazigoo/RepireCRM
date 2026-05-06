// frontend/crm-app/src/app/features/orders/order-form/order-form.component.ts
import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, AsyncPipe } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MAT_FORM_FIELD_DEFAULT_OPTIONS, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatStepper, MatStepperModule } from '@angular/material/stepper';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatChipsModule } from '@angular/material/chips';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { provideNativeDateAdapter } from '@angular/material/core';
import { Observable, startWith, map, of } from 'rxjs';
import { OrdersService } from '../../../services/orders.service';
import { CustomersService } from '../../../services/customers.service';
import { Customer, DeviceModel, AdditionalService } from '../../../core/models/models';

@Component({
  selector: 'app-order-form',
  standalone: true,
  imports: [
    NgIf, NgFor, AsyncPipe, ReactiveFormsModule,
    MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatStepperModule, MatAutocompleteModule,
    MatChipsModule, MatDatepickerModule, MatProgressSpinnerModule, MatSnackBarModule
  ],
  providers: [
    provideNativeDateAdapter(),
    {
      provide: MAT_FORM_FIELD_DEFAULT_OPTIONS,
      useValue: {
        appearance: 'outline',
        floatLabel: 'always'
      }
    }
  ],
  templateUrl: './order-form.component.html',
  styleUrl: './order-form.component.scss'
})
export class OrderFormComponent implements OnInit {
  orderForm!: FormGroup;
  customerForm!: FormGroup;
  deviceForm!: FormGroup;

  isEditMode = false;
  orderId: number | null = null;
  loading = false;
  creatingCustomer = false;

  // Data for form
  customers: Customer[] = [];
  filteredCustomers!: Observable<Customer[]>;
  deviceModels: DeviceModel[] = [];
  filteredDeviceModels!: Observable<DeviceModel[]>;
  additionalServices: AdditionalService[] = [];
  selectedServices: AdditionalService[] = [];

  readonly quickServiceLabels = ['Чехол', 'Защитное стекло', 'Диагностика'];

  // Form steps
  customerStepCompleted = false;
  deviceStepCompleted = false;

  private readonly moneyFormatter = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0
  });

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private ordersService: OrdersService,
    private customersService: CustomersService,
    private snackBar: MatSnackBar
  ) {
    // Инициализируем с пустым Observable, чтобы избежать ошибки
    this.filteredCustomers = of([]);
    this.filteredDeviceModels = of([]);
  }

  ngOnInit(): void {
    this.initializeForms();
    this.setupFilteredCustomers();
    this.setupFilteredDeviceModels();

    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.orderId = +params['id'];
        this.loadOrder(this.orderId);
      }
    });

    this.loadFormData();
  }

  private setupFilteredCustomers(): void {
    this.filteredCustomers = this.customerForm.get('customer')!.valueChanges.pipe(
      startWith(''),
      map(value => this.filterCustomers(value))
    );
  }

  private setupFilteredDeviceModels(): void {
    this.filteredDeviceModels = this.deviceForm.get('model')!.valueChanges.pipe(
      startWith(''),
      map(value => this.filterDeviceModels(value))
    );
  }

  private initializeForms(): void {
    this.customerForm = this.fb.group({
      customer: ['', Validators.required],
      newCustomer: this.fb.group({
        first_name: [''],
        last_name: [''],
        phone: [''],
        email: ['']
      })
    });

    this.deviceForm = this.fb.group({
      model: ['', Validators.required],
      model_id: [null],
      serial_number: [''],
      imei: [''],
      color: [''],
      storage_capacity: ['']
    });

    this.orderForm = this.fb.group({
      problem_description: ['', Validators.required],
      accessories: [''],
      device_condition: [''],
      cost_estimate: ['', [Validators.required, Validators.min(0)]],
      priority: ['normal'],
      estimated_completion: [''],
      notes: ['']
    });
  }

  private loadFormData(): void {
    // Load customers
    this.customersService.getCustomers().subscribe(customers => {
      this.customers = customers;
    });

    this.ordersService.getDeviceModels().subscribe(models => {
      this.deviceModels = models;
    });

    // Load additional services
    this.ordersService.getAdditionalServices().subscribe(services => {
      this.additionalServices = services;
    });
  }

  private loadOrder(id: number): void {
    this.loading = true;
    this.ordersService.getOrder(id).subscribe({
      next: (order) => {
        this.populateForm(order);
        this.loading = false;
      },
      error: (error) => {
        this.snackBar.open('Ошибка загрузки заказа', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  private populateForm(order: any): void {
    // Populate customer form
    this.customerForm.patchValue({
      customer: order.customer
    });

    // Populate device form
    this.deviceForm.patchValue({
      model: order.device.model,
      model_id: order.device.model.id,
      serial_number: order.device.serial_number,
      imei: order.device.imei,
      color: order.device.color,
      storage_capacity: order.device.storage_capacity
    });

    // Populate order form
    this.orderForm.patchValue({
      problem_description: order.problem_description,
      accessories: order.accessories,
      device_condition: order.device_condition,
      cost_estimate: order.cost_estimate,
      priority: order.priority,
      estimated_completion: order.estimated_completion ? new Date(order.estimated_completion) : null,
      notes: order.notes
    });

    this.selectedServices = order.additional_services
      .map((os: any) => os.service)
      .filter((service: AdditionalService | null | undefined): service is AdditionalService => Boolean(service));
  }

  private filterCustomers(value: any): Customer[] {
    if (!value || typeof value !== 'string') {
      return this.customers;
    }

    const filterValue = value.toLowerCase();
    return this.customers.filter(customer =>
      customer.first_name.toLowerCase().includes(filterValue) ||
      customer.last_name.toLowerCase().includes(filterValue) ||
      customer.phone.includes(filterValue)
    );
  }

  displayCustomer(customer: Customer): string {
    return customer ? `${customer.last_name} ${customer.first_name} (${customer.phone})` : '';
  }

  displayDeviceModel(model: DeviceModel | string): string {
    if (!model || typeof model === 'string') {
      return model || '';
    }
    return `${model.brand.name} ${model.name}`;
  }

  get selectedCustomer(): Customer | null {
    return this.getSelectedCustomer();
  }

  get selectedDeviceModel(): DeviceModel | null {
    return this.getSelectedDeviceModel();
  }

  get selectedDeviceName(): string {
    const selectedModel = this.getSelectedDeviceModel();
    if (selectedModel) {
      return this.displayDeviceModel(selectedModel);
    }

    const modelValue = this.deviceForm?.get('model')?.value;
    if (typeof modelValue === 'string' && modelValue.trim()) {
      return modelValue.trim();
    }

    return 'Устройство не выбрано';
  }

  get selectedCustomerName(): string {
    const customer = this.getSelectedCustomer();
    if (!customer) {
      return 'Клиент не выбран';
    }

    return `${customer.last_name} ${customer.first_name}`.trim();
  }

  get selectedCustomerPhone(): string {
    return this.getSelectedCustomer()?.phone || 'Телефон не указан';
  }

  get popularDeviceModels(): DeviceModel[] {
    return this.deviceModels.slice(0, 8);
  }

  get servicesTotal(): number {
    return this.selectedServices.reduce((sum, service) => sum + Number(service.price || 0), 0);
  }

  get quickServices(): Array<{ label: string; service: AdditionalService | null; selected: boolean }> {
    return this.quickServiceLabels.map(label => {
      const service = this.findServiceByLabel(label);
      return {
        label,
        service,
        selected: service ? this.isServiceSelected(service) : false
      };
    });
  }

  get estimatedBaseCost(): number {
    return Number(this.orderForm?.get('cost_estimate')?.value || 0);
  }

  get estimatedTotal(): number {
    return this.estimatedBaseCost + this.servicesTotal;
  }

  get orderProblemPreview(): string {
    const value = String(this.orderForm?.get('problem_description')?.value || '').trim();
    return value || 'Описание проблемы появится здесь';
  }

  get isCustomerReady(): boolean {
    return Boolean(this.getSelectedCustomer());
  }

  get isDeviceReady(): boolean {
    return Boolean(this.getSelectedDeviceModel());
  }

  get isOrderReady(): boolean {
    return this.orderForm?.valid || false;
  }

  getCustomerInitials(customer: Customer | null): string {
    if (!customer) {
      return 'К';
    }

    const first = customer.first_name?.charAt(0) || '';
    const last = customer.last_name?.charAt(0) || '';
    return `${last}${first}`.toUpperCase() || 'К';
  }

  getPriorityLabel(priority: string | null | undefined): string {
    const labels: Record<string, string> = {
      low: 'Низкий',
      normal: 'Обычный',
      high: 'Высокий',
      urgent: 'Срочный'
    };
    return labels[priority || 'normal'] || 'Обычный';
  }

  formatMoney(value: number | null | undefined): string {
    return `${this.moneyFormatter.format(Number(value || 0))} ₽`;
  }

  trackById(_: number, item: { id: number }): number {
    return item.id;
  }

  onDeviceModelSelected(model: DeviceModel): void {
    this.deviceForm.patchValue({
      model,
      model_id: model.id
    });
  }

  selectPopularDeviceModel(model: DeviceModel): void {
    this.onDeviceModelSelected(model);
  }

  onCustomerStepNext(stepper: MatStepper): void {
    if (this.getSelectedCustomer()) {
      this.customerForm.get('customer')?.setErrors(null);
      this.customerStepCompleted = true;
      stepper.next();
      return;
    }

    this.customerForm.get('customer')?.setErrors({ required: true });
    this.customerForm.get('customer')?.markAsTouched();
    this.snackBar.open('Выберите клиента из списка или добавьте нового', 'Закрыть', {
      duration: 3000
    });
  }

  createCustomerAndContinue(stepper: MatStepper): void {
    const newCustomer = this.customerForm.get('newCustomer') as FormGroup;
    const value = newCustomer.getRawValue();
    const firstName = (value.first_name || '').trim();
    const lastName = (value.last_name || '').trim();
    const phone = (value.phone || '').trim();
    const email = (value.email || '').trim();

    if (!firstName || !lastName || !phone) {
      newCustomer.markAllAsTouched();
      this.snackBar.open('Заполните имя, фамилию и телефон клиента', 'Закрыть', {
        duration: 3000
      });
      return;
    }

    this.creatingCustomer = true;
    this.customersService.createCustomer({
      first_name: firstName,
      last_name: lastName,
      phone,
      email: email || undefined
    }).subscribe({
      next: (customer) => {
        this.customers = [customer, ...this.customers.filter(item => item.id !== customer.id)];
        this.customerForm.patchValue({ customer });
        this.customerForm.get('customer')?.setErrors(null);
        newCustomer.reset();
        this.creatingCustomer = false;
        this.customerStepCompleted = true;
        this.snackBar.open('Клиент добавлен', 'Закрыть', { duration: 2500 });
        stepper.next();
      },
      error: (error) => {
        const message = error?.error?.error || 'Не удалось добавить клиента';
        this.snackBar.open(message, 'Закрыть', { duration: 4000 });
        this.creatingCustomer = false;
      }
    });
  }

  onDeviceStepNext(stepper: MatStepper): void {
    if (!this.deviceForm.get('model')?.value) {
      this.deviceForm.get('model')?.markAsTouched();
      return;
    }

    const selectedModel = this.getSelectedDeviceModel();
    if (selectedModel) {
      this.deviceForm.patchValue({ model_id: selectedModel.id });
      this.deviceStepCompleted = true;
      stepper.next();
      return;
    }

    const modelQuery = String(this.deviceForm.get('model')?.value || '').trim();
    if (modelQuery.length < 2) {
      this.snackBar.open('Укажите модель устройства', 'Закрыть', { duration: 3000 });
      return;
    }

    const parsed = this.parseDeviceModel(modelQuery);
    this.loading = true;
    this.ordersService.createDeviceModel({
      brand_name: parsed.brandName,
      name: parsed.modelName,
      device_type_name: parsed.deviceTypeName
    }).subscribe({
      next: (model) => {
        this.deviceModels = [model, ...this.deviceModels.filter(item => item.id !== model.id)];
        this.deviceForm.patchValue({
          model,
          model_id: model.id
        });
        this.deviceStepCompleted = true;
        this.loading = false;
        this.snackBar.open('Модель устройства добавлена в справочник', 'Закрыть', {
          duration: 2500
        });
        stepper.next();
      },
      error: (error) => {
        const message = error?.error?.error || 'Не удалось добавить модель устройства';
        this.snackBar.open(message, 'Закрыть', { duration: 4000 });
        this.loading = false;
      }
    });
  }

  addService(service: AdditionalService): void {
    if (!this.isServiceSelected(service)) {
      this.selectedServices.push(service);
      this.updateTotalCost();
    }
  }

  removeService(service: AdditionalService): void {
    this.selectedServices = this.selectedServices.filter(s => s.id !== service.id);
    this.updateTotalCost();
  }

  toggleService(service: AdditionalService): void {
    if (this.isServiceSelected(service)) {
      this.removeService(service);
      return;
    }

    this.addService(service);
  }

  addQuickService(label: string): void {
    const service = this.findServiceByLabel(label);
    if (!service) {
      this.snackBar.open(`Услуга "${label}" не найдена в справочнике`, 'Закрыть', {
        duration: 3000
      });
      return;
    }

    if (this.isServiceSelected(service)) {
      this.snackBar.open(`${service.name} уже добавлен в заказ`, 'Закрыть', {
        duration: 2200
      });
      return;
    }

    this.addService(service);
    this.snackBar.open(`${service.name} добавлен в заказ`, 'Закрыть', {
      duration: 2200
    });
  }

  isServiceSelected(service: AdditionalService): boolean {
    return this.selectedServices.some(selected => selected.id === service.id);
  }

  private updateTotalCost(): void {
    const baseCost = this.orderForm.get('cost_estimate')?.value || 0;
    const servicesCost = this.selectedServices.reduce((sum, service) => sum + service.price, 0);
    // Update display or form field as needed
  }

  onSubmit(): void {
    if (this.isFormValid()) {
      this.loading = true;

      const formData = this.buildFormData();

      const request = this.isEditMode
        ? this.ordersService.updateOrder(this.orderId!, formData)
        : this.ordersService.createOrder(formData);

      request.subscribe({
        next: (order) => {
          const message = this.isEditMode ? 'Заказ обновлен' : 'Заказ создан';
          this.snackBar.open(message, 'Закрыть', { duration: 3000 });
          this.router.navigate(['/orders', order.id]);
        },
        error: (error) => {
          const message = error?.error?.error ||
            error?.error?.detail?.[0]?.msg ||
            'Ошибка сохранения заказа';
          this.snackBar.open(message, 'Закрыть', { duration: 4000 });
          this.loading = false;
        }
      });
      return;
    }

    this.customerForm.markAllAsTouched();
    this.deviceForm.markAllAsTouched();
    this.orderForm.markAllAsTouched();
    this.snackBar.open('Заполните обязательные поля заказа', 'Закрыть', { duration: 3000 });
  }

  private isFormValid(): boolean {
    return !!this.getSelectedCustomer() && this.deviceForm.valid && this.orderForm.valid;
  }

  private buildFormData(): any {
    const customer = this.getSelectedCustomer();
    const device = {
      model_id: this.deviceForm.get('model_id')?.value,
      serial_number: this.deviceForm.get('serial_number')?.value,
      imei: this.deviceForm.get('imei')?.value,
      color: this.deviceForm.get('color')?.value,
      storage_capacity: this.deviceForm.get('storage_capacity')?.value
    };
    const order = this.orderForm.value;
    const estimatedCompletion = this.normalizeDateTime(order.estimated_completion);

    const payload: any = {
      customer_id: customer!.id,
      device: device,
      problem_description: order.problem_description,
      accessories: order.accessories,
      device_condition: order.device_condition,
      cost_estimate: order.cost_estimate,
      priority: order.priority,
      additional_services: this.selectedServices.map(service => ({
        service_id: service.id,
        quantity: 1
      }))
    };

    if (estimatedCompletion) {
      payload.estimated_completion = estimatedCompletion;
    }

    return payload;
  }

  cancel(): void {
    this.router.navigate(['/orders']);
  }

  private getSelectedCustomer(): Customer | null {
    const customer = this.customerForm.get('customer')?.value;
    if (customer && typeof customer === 'object' && 'id' in customer) {
      return customer as Customer;
    }
    return null;
  }

  private filterDeviceModels(value: DeviceModel | string): DeviceModel[] {
    if (!value || typeof value !== 'string') {
      return this.deviceModels.slice(0, 30);
    }

    const filterValue = value.toLowerCase();
    return this.deviceModels.filter(model => {
      const fullName = `${model.brand.name} ${model.name}`.toLowerCase();
      const modelNumber = model.model_number?.toLowerCase() || '';
      return fullName.includes(filterValue) ||
        modelNumber.includes(filterValue);
    }).slice(0, 30);
  }

  private getSelectedDeviceModel(): DeviceModel | null {
    const model = this.deviceForm.get('model')?.value;
    if (model && typeof model === 'object' && 'id' in model) {
      return model as DeviceModel;
    }

    const query = String(model || '').trim().toLowerCase();
    return this.deviceModels.find(candidate =>
      `${candidate.brand.name} ${candidate.name}`.toLowerCase() === query
    ) || null;
  }

  private findServiceByLabel(label: string): AdditionalService | null {
    const normalizedLabel = label.toLowerCase();
    return this.additionalServices.find(service =>
      service.name.toLowerCase() === normalizedLabel
    ) || this.additionalServices.find(service => {
      const serviceName = service.name.toLowerCase();
      return serviceName.includes(normalizedLabel) || normalizedLabel.includes(serviceName);
    }) || null;
  }

  private normalizeDateTime(value: Date | string | null | undefined): string | undefined {
    if (!value) {
      return undefined;
    }

    if (value instanceof Date) {
      return value.toISOString();
    }

    const trimmed = String(value).trim();
    return trimmed || undefined;
  }

  private parseDeviceModel(value: string): {
    brandName: string;
    modelName: string;
    deviceTypeName: string;
  } {
    const knownBrands = [
      'Apple', 'Samsung', 'Xiaomi', 'Redmi', 'Poco', 'Huawei', 'Honor', 'Realme',
      'Tecno', 'Infinix', 'Oppo', 'Vivo', 'OnePlus', 'Google', 'Sony', 'Nokia',
      'Lenovo', 'Asus', 'Acer', 'HP', 'Dell', 'MSI'
    ];
    const normalized = value.replace(/\s+/g, ' ').trim();
    const foundBrand = knownBrands.find(brand =>
      normalized.toLowerCase().startsWith(brand.toLowerCase())
    );

    if (foundBrand) {
      return {
        brandName: foundBrand,
        modelName: normalized.slice(foundBrand.length).trim() || normalized,
        deviceTypeName: 'Смартфон'
      };
    }

    const [brandName, ...modelParts] = normalized.split(' ');
    return {
      brandName: brandName || 'Другое',
      modelName: modelParts.join(' ') || normalized,
      deviceTypeName: 'Смартфон'
    };
  }
}

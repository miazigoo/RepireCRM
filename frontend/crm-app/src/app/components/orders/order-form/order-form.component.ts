// frontend/crm-app/src/app/features/orders/order-form/order-form.component.ts
import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, AsyncPipe } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatStepperModule } from '@angular/material/stepper';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatChipsModule } from '@angular/material/chips';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { provideNativeDateAdapter } from '@angular/material/core';
import { Observable, startWith, map } from 'rxjs';
import { OrdersService } from '../../../core/services/orders.service';
import { CustomersService } from '../../../core/services/customers.service';
import { Customer, DeviceModel, AdditionalService } from '../../../core/models/models';

@Component({
  selector: 'app-order-form',
  standalone: true,
  imports: [
    NgIf, NgFor, AsyncPipe, ReactiveFormsModule,
    MatCardModule, MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatIconModule, MatStepperModule, MatAutocompleteModule,
    MatChipsModule, MatDatepickerModule, MatProgressSpinnerModule, MatSnackBarModule
  ],
  providers: [provideNativeDateAdapter()],
  templateUrl: './order-form.component.html',
  styleUrl: './order-form.component.css'
})
export class OrderFormComponent implements OnInit {
  orderForm: FormGroup;
  customerForm: FormGroup;
  deviceForm: FormGroup;

  isEditMode = false;
  orderId: number | null = null;
  loading = false;

  // Data for form
  customers: Customer[] = [];
  filteredCustomers: Observable<Customer[]>;
  deviceModels: DeviceModel[] = [];
  additionalServices: AdditionalService[] = [];
  selectedServices: AdditionalService[] = [];

  // Form steps
  customerStepCompleted = false;
  deviceStepCompleted = false;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private ordersService: OrdersService,
    private customersService: CustomersService,
    private snackBar: MatSnackBar
  ) {
    this.initializeForms();
    this.filteredCustomers = this.customerForm.get('customer')!.valueChanges.pipe(
      startWith(''),
      map(value => this.filterCustomers(value))
    );
  }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.orderId = +params['id'];
        this.loadOrder(this.orderId);
      }
    });

    this.loadFormData();
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
      model_id: ['', Validators.required],
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

    // Load device models (would come from a device service)
    // this.deviceService.getDeviceModels().subscribe(models => {
    //   this.deviceModels = models;
    // });

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

    this.selectedServices = order.additional_services.map((os: any) => os.service);
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

  onCustomerStepNext(): void {
    if (this.customerForm.valid) {
      this.customerStepCompleted = true;
    }
  }

  onDeviceStepNext(): void {
    if (this.deviceForm.valid) {
      this.deviceStepCompleted = true;
    }
  }

  addService(service: AdditionalService): void {
    if (!this.selectedServices.find(s => s.id === service.id)) {
      this.selectedServices.push(service);
      this.updateTotalCost();
    }
  }

  removeService(service: AdditionalService): void {
    this.selectedServices = this.selectedServices.filter(s => s.id !== service.id);
    this.updateTotalCost();
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
          this.snackBar.open('Ошибка сохранения заказа', 'Закрыть', { duration: 3000 });
          this.loading = false;
        }
      });
    }
  }

  private isFormValid(): boolean {
    return this.customerForm.valid && this.deviceForm.valid && this.orderForm.valid;
  }

  private buildFormData(): any {
    const customer = this.customerForm.get('customer')?.value;
    const device = this.deviceForm.value;
    const order = this.orderForm.value;

    return {
      customer_id: customer.id,
      device: device,
      problem_description: order.problem_description,
      accessories: order.accessories,
      device_condition: order.device_condition,
      cost_estimate: order.cost_estimate,
      priority: order.priority,
      estimated_completion: order.estimated_completion,
      additional_services: this.selectedServices.map(service => ({
        service_id: service.id,
        quantity: 1
      }))
    };
  }

  cancel(): void {
    this.router.navigate(['/orders']);
  }
}

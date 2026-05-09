import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AdditionalService, Shop } from '../../../core/models/models';
import { AuthService } from '../../../services/auth.service';
import { OrdersService } from '../../../services/orders.service';

interface ServiceCategory {
  value: string;
  label: string;
}

@Component({
  selector: 'app-services-management',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  templateUrl: './services-management.component.html',
  styleUrl: './services-management.component.scss',
})
export class ServicesManagementComponent implements OnInit {
  readonly categories: ServiceCategory[] = [
    { value: 'protection', label: 'Защитные покрытия' },
    { value: 'accessories', label: 'Аксессуары' },
    { value: 'software', label: 'Программное обеспечение' },
    { value: 'cleaning', label: 'Чистка' },
    { value: 'other', label: 'Прочее' },
  ];

  services: AdditionalService[] = [];
  shops: Shop[] = [];
  serviceForm: FormGroup;
  editingService: AdditionalService | null = null;
  loading = false;
  saving = false;

  constructor(
    private fb: FormBuilder,
    private ordersService: OrdersService,
    private authService: AuthService,
    private snackBar: MatSnackBar,
  ) {
    this.serviceForm = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(100)]],
      category: ['other', Validators.required],
      price: [0, [Validators.required, Validators.min(0)]],
      description: [''],
      shop_ids: [[]],
      is_active: [true],
    });
  }

  ngOnInit(): void {
    this.loadServices();
    this.loadShops();
  }

  loadServices(): void {
    this.loading = true;
    this.ordersService.getAdditionalServices(true).subscribe({
      next: (services) => {
        this.services = services;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.snackBar.open('Не удалось загрузить услуги', 'Закрыть', { duration: 4000 });
      },
    });
  }

  loadShops(): void {
    this.authService.getAvailableShops().subscribe({
      next: (shops) => {
        this.shops = shops.filter((shop) => shop.is_active);
      },
      error: () => {
        this.shops = [];
      },
    });
  }

  saveService(): void {
    if (this.serviceForm.invalid) {
      this.serviceForm.markAllAsTouched();
      return;
    }

    this.saving = true;
    const payload = this.serviceForm.getRawValue();
    const request$ = this.editingService
      ? this.ordersService.updateAdditionalService(this.editingService.id, payload)
      : this.ordersService.createAdditionalService(payload);

    request$.subscribe({
      next: () => {
        this.saving = false;
        this.resetForm();
        this.loadServices();
        this.snackBar.open('Услуга сохранена', 'Закрыть', { duration: 2500 });
      },
      error: (error) => {
        this.saving = false;
        this.snackBar.open(this.extractError(error), 'Закрыть', { duration: 4500 });
      },
    });
  }

  editService(service: AdditionalService): void {
    this.editingService = service;
    this.serviceForm.patchValue({
      name: service.name,
      category: service.category,
      price: Number(service.price || 0),
      description: service.description || '',
      shop_ids: service.shop_ids || [],
      is_active: service.is_active !== false,
    });
  }

  disableService(service: AdditionalService): void {
    this.ordersService.deleteAdditionalService(service.id).subscribe({
      next: () => {
        this.loadServices();
        this.snackBar.open('Услуга отключена', 'Закрыть', { duration: 2500 });
      },
      error: (error) => {
        this.snackBar.open(this.extractError(error), 'Закрыть', { duration: 4500 });
      },
    });
  }

  resetForm(): void {
    this.editingService = null;
    this.serviceForm.reset({
      name: '',
      category: 'other',
      price: 0,
      description: '',
      shop_ids: [],
      is_active: true,
    });
  }

  getCategoryLabel(category: string): string {
    return this.categories.find((item) => item.value === category)?.label || category;
  }

  getServiceScope(service: AdditionalService): string {
    if (!service.shop_ids?.length) {
      return 'Все филиалы';
    }
    const names = this.shops
      .filter((shop) => service.shop_ids?.includes(shop.id))
      .map((shop) => shop.name);
    return names.join(', ') || `${service.shop_ids.length} филиалов`;
  }

  formatMoney(value: number): string {
    return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(value || 0)} ₽`;
  }

  trackById(_: number, item: AdditionalService): number {
    return item.id;
  }

  private extractError(error: any): string {
    return error?.error?.error || error?.error?.detail || 'Не удалось сохранить услугу';
  }
}

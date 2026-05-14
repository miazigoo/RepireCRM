// frontend/crm-app/src/app/components/admin/shop-management/shop-management.component.ts
import { Component, OnInit, ViewChild } from '@angular/core';
import { NgIf, NgFor, DatePipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator, MatPaginatorIntl } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { AdminService, ShopCreateRequest } from '../../../services/admin.service';
import { Shop } from '../../../core/models/models';
import { MatDividerModule } from '@angular/material/divider';
import { RussianPaginatorIntl } from '../../../core/i18n/russian-paginator-intl';

@Component({
  selector: 'app-shop-management',
  standalone: true,
  imports: [
    NgIf,
    NgFor,
    RouterModule,
    ReactiveFormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatMenuModule,
    MatChipsModule,
    MatDialogModule,
    MatSnackBarModule,
    MatSlideToggleModule,
    MatDividerModule,
  ],
  templateUrl: './shop-management.component.html',
  styleUrl: './shop-management.component.scss',
  providers: [{ provide: MatPaginatorIntl, useClass: RussianPaginatorIntl }],
})
export class ShopManagementComponent implements OnInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  displayedColumns: string[] = [
    'name',
    'city',
    'address',
    'coordinates',
    'contacts',
    'is_active',
    'actions',
  ];

  dataSource = new MatTableDataSource<Shop>();
  loading = false;
  showForm = false;
  editingShop: Shop | null = null;

  shopForm: FormGroup;

  timezoneOptions = [
    { value: 'Europe/Moscow', label: 'Москва (UTC+3)' },
    { value: 'Europe/Samara', label: 'Самара (UTC+4)' },
    { value: 'Asia/Yekaterinburg', label: 'Екатеринбург (UTC+5)' },
    { value: 'Asia/Novosibirsk', label: 'Новосибирск (UTC+7)' },
    { value: 'Asia/Krasnoyarsk', label: 'Красноярск (UTC+7)' },
    { value: 'Asia/Irkutsk', label: 'Иркутск (UTC+8)' },
    { value: 'Asia/Vladivostok', label: 'Владивосток (UTC+10)' },
  ];

  currencyOptions = [
    { value: 'RUB', label: 'Российский рубль (₽)' },
    { value: 'USD', label: 'Доллар США ($)' },
    { value: 'EUR', label: 'Евро (€)' },
  ];

  constructor(
    private adminService: AdminService,
    private fb: FormBuilder,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {
    this.shopForm = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(100)]],
      code: [
        '',
        [Validators.required, Validators.maxLength(10), Validators.pattern(/^[A-Z0-9]+$/)],
      ],
      city: ['', Validators.maxLength(100)],
      address: [''],
      latitude: [null, [Validators.min(-90), Validators.max(90)]],
      longitude: [null, [Validators.min(-180), Validators.max(180)]],
      phone: ['', Validators.pattern(/^\+?[0-9\s().-]{7,24}$/)],
      email: ['', Validators.email],
      timezone: ['Europe/Moscow', Validators.required],
      currency: ['RUB', Validators.required],
    });
  }

  ngOnInit(): void {
    this.loadShops();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  get mobileShops(): Shop[] {
    const shops = this.dataSource.filter ? this.dataSource.filteredData : this.dataSource.data;
    const pageSize = this.paginator?.pageSize || shops.length || 20;
    const pageIndex = this.paginator?.pageIndex || 0;
    const start = pageIndex * pageSize;
    return shops.slice(start, start + pageSize);
  }

  private loadShops(): void {
    this.loading = true;
    this.adminService.getShops().subscribe({
      next: (shops) => {
        this.dataSource.data = shops;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading shops:', error);
        this.snackBar.open('Ошибка загрузки магазинов', 'Закрыть', { duration: 3000 });
        this.loading = false;
      },
    });
  }

  showCreateForm(): void {
    this.showForm = true;
    this.editingShop = null;
    this.shopForm.reset({
      timezone: 'Europe/Moscow',
      currency: 'RUB',
    });
  }

  editShop(shop: Shop): void {
    this.showForm = true;
    this.editingShop = shop;
    this.shopForm.patchValue(shop);
  }

  cancelForm(): void {
    this.showForm = false;
    this.editingShop = null;
    this.shopForm.reset();
  }

  onSubmit(): void {
    if (this.shopForm.valid) {
      this.loading = true;
      const raw = this.shopForm.value;
      const formData: ShopCreateRequest = {
        ...raw,
        latitude: raw.latitude === '' || raw.latitude == null ? null : Number(raw.latitude),
        longitude: raw.longitude === '' || raw.longitude == null ? null : Number(raw.longitude),
      };

      const request = this.editingShop
        ? this.adminService.updateShop(this.editingShop.id, formData)
        : this.adminService.createShop(formData);

      request.subscribe({
        next: (shop) => {
          const message = this.editingShop ? 'Магазин обновлен' : 'Магазин создан';
          this.snackBar.open(message, 'Закрыть', { duration: 3000 });
          this.cancelForm();
          this.loadShops();
        },
        error: (error) => {
          const errorMessage = error.error?.error || 'Ошибка сохранения магазина';
          this.snackBar.open(errorMessage, 'Закрыть', { duration: 5000 });
          this.loading = false;
        },
      });
    } else {
      this.markFormGroupTouched();
    }
  }

  toggleShopStatus(shop: Shop): void {
    const newStatus = !shop.is_active;
    // Создать правильный объект для обновления
    const updateData: Partial<Shop> = {
      is_active: newStatus,
    };

    this.adminService.updateShop(shop.id, updateData).subscribe({
      next: (updatedShop) => {
        shop.is_active = updatedShop.is_active;
        const statusText = newStatus ? 'активирован' : 'деактивирован';
        this.snackBar.open(`Магазин ${statusText}`, 'Закрыть', { duration: 3000 });
      },
      error: (error) => {
        this.snackBar.open('Ошибка изменения статуса магазина', 'Закрыть', { duration: 3000 });
      },
    });
  }

  deleteShop(shop: Shop): void {
    if (confirm(`Удалить магазин "${shop.name}"? Это действие нельзя отменить.`)) {
      this.adminService.deleteShop(shop.id).subscribe({
        next: () => {
          this.snackBar.open('Магазин удален', 'Закрыть', { duration: 3000 });
          this.loadShops();
        },
        error: (error) => {
          const errorMessage = error.error?.error || 'Ошибка удаления магазина';
          this.snackBar.open(errorMessage, 'Закрыть', { duration: 5000 });
        },
      });
    }
  }

  private markFormGroupTouched(): void {
    Object.keys(this.shopForm.controls).forEach((key) => {
      const control = this.shopForm.get(key);
      control?.markAsTouched();
    });
  }

  getFieldError(fieldName: string): string {
    const control = this.shopForm.get(fieldName);
    if (control?.errors && control.touched) {
      if (control.errors['required']) {
        return 'Поле обязательно для заполнения';
      }
      if (control.errors['email']) {
        return 'Введите корректный email';
      }
      if (control.errors['pattern']) {
        if (fieldName === 'code') {
          return 'Код должен содержать только заглавные буквы и цифры';
        }
        return 'Введите корректный номер телефона';
      }
      if (control.errors['min'] || control.errors['max']) {
        if (fieldName === 'latitude') {
          return 'Широта должна быть от -90 до 90';
        }
        if (fieldName === 'longitude') {
          return 'Долгота должна быть от -180 до 180';
        }
      }
      if (control.errors['maxlength']) {
        return `Максимум ${control.errors['maxlength'].requiredLength} символов`;
      }
    }
    return '';
  }

  getTimezoneLabel(timezone: string): string {
    const option = this.timezoneOptions.find((opt) => opt.value === timezone);
    return option ? option.label : timezone;
  }

  getCurrencyLabel(currency: string): string {
    const option = this.currencyOptions.find((opt) => opt.value === currency);
    return option ? option.label : currency;
  }

  getCoordinateText(shop: Shop): string {
    if (shop.latitude == null || shop.longitude == null) {
      return '';
    }
    return `${Number(shop.latitude).toFixed(6)}, ${Number(shop.longitude).toFixed(6)}`;
  }
}

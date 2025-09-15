// frontend/crm-app/src/app/components/admin/shop-management/shop-management.component.ts
import { Component, OnInit, ViewChild } from '@angular/core';
import { NgIf, NgFor, DatePipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { AdminService, ShopCreateRequest } from '../../../services/admin.service';
import { Shop } from '../../../core/models/models';

@Component({
  selector: 'app-shop-management',
  standalone: true,
  imports: [
    NgIf, NgFor, DatePipe, RouterModule, ReactiveFormsModule,
    MatTableModule, MatPaginatorModule, MatSortModule, MatInputModule,
    MatSelectModule, MatButtonModule, MatIconModule, MatCardModule,
    MatProgressSpinnerModule, MatMenuModule, MatChipsModule,
    MatDialogModule, MatSnackBarModule, MatSlideToggleModule
  ],
  templateUrl: './shop-management.component.html',
  styleUrl: './shop-management.component.css'
})
export class ShopManagementComponent implements OnInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  displayedColumns: string[] = [
    'name',
    'code',
    'address',
    'phone',
    'email',
    'is_active',
    'actions'
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
    { value: 'Asia/Vladivostok', label: 'Владивосток (UTC+10)' }
  ];

  currencyOptions = [
    { value: 'RUB', label: 'Российский рубль (₽)' },
    { value: 'USD', label: 'Доллар США ($)' },
    { value: 'EUR', label: 'Евро (€)' }
  ];

  constructor(
    private adminService: AdminService,
    private fb: FormBuilder,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {
    this.shopForm = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(100)]],
      code: ['', [Validators.required, Validators.maxLength(10), Validators.pattern(/^[A-Z0-9]+$/)]],
      address: [''],
      phone: ['', Validators.pattern(/^\+?[1-9]\d{1,14}$/)],
      email: ['', Validators.email],
      timezone: ['Europe/Moscow', Validators.required],
      currency: ['RUB', Validators.required]
    });
  }

  ngOnInit(): void {
    this.loadShops();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
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
      }
    });
  }

  showCreateForm(): void {
    this.showForm = true;
    this.editingShop = null;
    this.shopForm.reset({
      timezone: 'Europe/Moscow',
      currency: 'RUB'
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
      const formData: ShopCreateRequest = this.shopForm.value;

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
        }
      });
    } else {
      this.markFormGroupTouched();
    }
  }

  toggleShopStatus(shop: Shop): void {
    const newStatus = !shop.is_active;
    this.adminService.updateShop(shop.id, { is_active: newStatus }).subscribe({
      next: (updatedShop) => {
        shop.is_active = updatedShop.is_active;
        const statusText = newStatus ? 'активирован' : 'деактивирован';
        this.snackBar.open(`Магазин ${statusText}`, 'Закрыть', { duration: 3000 });
      },
      error: (error) => {
        this.snackBar.open('Ошибка изменения статуса магазина', 'Закрыть', { duration: 3000 });
      }
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
        }
      });
    }
  }

  private markFormGroupTouched(): void {
    Object.keys(this.shopForm.controls).forEach(key => {
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
      if (control.errors['maxlength']) {
        return `Максимум ${control.errors['maxlength'].requiredLength} символов`;
      }
    }
    return '';
  }

  getTimezoneLabel(timezone: string): string {
    const option = this.timezoneOptions.find(opt => opt.value === timezone);
    return option ? option.label : timezone;
  }

  getCurrencyLabel(currency: string): string {
    const option = this.currencyOptions.find(opt => opt.value === currency);
    return option ? option.label : currency;
  }
}

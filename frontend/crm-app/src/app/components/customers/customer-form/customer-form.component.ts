import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MAT_FORM_FIELD_DEFAULT_OPTIONS, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { provideNativeDateAdapter } from '@angular/material/core';
import { CustomersService } from '../../../services/customers.service';
import { Customer, CustomerPayload } from '../../../core/models/models';

@Component({
  selector: 'app-customer-form',
  standalone: true,
  imports: [
    NgIf, NgFor, ReactiveFormsModule,
    MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatIconModule, MatDatepickerModule,
    MatProgressSpinnerModule, MatSnackBarModule, MatCheckboxModule
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
  templateUrl: './customer-form.component.html',
  styleUrl: './customer-form.component.scss'
})
export class CustomerFormComponent implements OnInit {
  customerForm: FormGroup;
  isEditMode = false;
  customerId: number | null = null;
  loading = false;

  sourceOptions = [
    { value: 'website', label: 'Сайт' },
    { value: 'social', label: 'Социальные сети' },
    { value: 'referral', label: 'Рекомендация' },
    { value: 'advertising', label: 'Реклама' },
    { value: 'walk_in', label: 'Зашел с улицы' },
    { value: 'other', label: 'Другое' }
  ];

  channelOptions = [
    { value: '', label: 'Не выбран' },
    { value: 'sms', label: 'SMS' },
    { value: 'email', label: 'Email' }
  ];

  private readonly phonePattern = /^(\+?\d[\d\s().-]{6,20})$/;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private customersService: CustomersService,
    private snackBar: MatSnackBar
  ) {
    this.customerForm = this.fb.group({
      first_name: ['', [Validators.required, Validators.maxLength(50)]],
      last_name: ['', [Validators.required, Validators.maxLength(50)]],
      middle_name: ['', Validators.maxLength(50)],
      phone: ['', [Validators.required, Validators.pattern(this.phonePattern)]],
      email: ['', [Validators.email, Validators.maxLength(254)]],
      source: [''],
      source_details: ['', Validators.maxLength(200)],
      birth_date: [''],
      preferred_channel: [''],
      marketing_consent: [false],
      notes: ['', Validators.maxLength(1000)]
    });
  }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.customerId = +params['id'];
        this.loadCustomer(this.customerId);
      }
    });
  }

  private loadCustomer(id: number): void {
    this.loading = true;
    this.customersService.getCustomer(id).subscribe({
      next: (customer) => {
        this.populateForm(customer);
        this.loading = false;
      },
      error: (error) => {
        this.snackBar.open('Ошибка загрузки клиента', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  private populateForm(customer: Customer): void {
    this.customerForm.patchValue({
      first_name: customer.first_name,
      last_name: customer.last_name,
      middle_name: customer.middle_name,
      phone: customer.phone,
      email: customer.email,
      source: customer.source,
      source_details: customer.source_details,
      birth_date: customer.birth_date ? new Date(customer.birth_date) : null,
      preferred_channel: customer.preferred_channel || '',
      marketing_consent: customer.marketing_consent,
      notes: customer.notes
    });
  }

  onSubmit(): void {
    this.trimTextControls();

    if (this.customerForm.valid) {
      this.loading = true;

      const formData = this.buildPayload();

      const request = this.isEditMode
        ? this.customersService.updateCustomer(this.customerId!, formData)
        : this.customersService.createCustomer(formData);

      request.subscribe({
        next: (customer) => {
          const message = this.isEditMode ? 'Клиент обновлен' : 'Клиент создан';
          this.snackBar.open(message, 'Закрыть', { duration: 3000 });
          this.router.navigate(['/customers', customer.id]);
        },
        error: (error) => {
          const errorMessage = error.error?.error || 'Ошибка сохранения клиента';
          this.snackBar.open(errorMessage, 'Закрыть', { duration: 5000 });
          this.loading = false;
        }
      });
    } else {
      this.markFormGroupTouched();
    }
  }

  private trimTextControls(): void {
    [
      'first_name',
      'last_name',
      'middle_name',
      'phone',
      'email',
      'source_details',
      'notes'
    ].forEach(field => {
      const control = this.customerForm.get(field);
      const value = control?.value;
      if (typeof value === 'string') {
        control?.setValue(value.trim(), { emitEvent: false });
      }
    });
  }

  private buildPayload(): CustomerPayload {
    const value = this.customerForm.getRawValue();
    const birthDate = value.birth_date instanceof Date
      ? value.birth_date.toISOString().slice(0, 10)
      : value.birth_date || null;

    return {
      first_name: (value.first_name || '').trim(),
      last_name: (value.last_name || '').trim(),
      middle_name: (value.middle_name || '').trim(),
      phone: (value.phone || '').trim(),
      email: (value.email || '').trim(),
      source: value.source || '',
      source_details: (value.source_details || '').trim(),
      birth_date: birthDate,
      preferred_channel: value.preferred_channel || '',
      marketing_consent: Boolean(value.marketing_consent),
      notes: (value.notes || '').trim()
    };
  }

  private markFormGroupTouched(): void {
    Object.keys(this.customerForm.controls).forEach(key => {
      const control = this.customerForm.get(key);
      control?.markAsTouched();
    });
  }

  cancel(): void {
    if (this.isEditMode) {
      this.router.navigate(['/customers', this.customerId]);
    } else {
      this.router.navigate(['/customers']);
    }
  }

  getFieldError(fieldName: string): string {
    const control = this.customerForm.get(fieldName);
    if (control?.errors && control.touched) {
      if (control.errors['required']) {
        return 'Поле обязательно для заполнения';
      }
      if (control.errors['email']) {
        return 'Введите корректный email';
      }
      if (control.errors['pattern']) {
        return 'Введите корректный номер телефона';
      }
      if (control.errors['maxlength']) {
        return `Максимум ${control.errors['maxlength'].requiredLength} символов`;
      }
    }
    return '';
  }

  get formTitle(): string {
    return this.isEditMode ? 'Редактирование клиента' : 'Новый клиент';
  }

  get previewName(): string {
    const value = this.customerForm.getRawValue();
    return [value.last_name, value.first_name, value.middle_name].filter(Boolean).join(' ') || 'Клиент';
  }

  get previewInitials(): string {
    const value = this.customerForm.getRawValue();
    const first = value.first_name?.charAt(0) || '';
    const last = value.last_name?.charAt(0) || '';
    return `${last}${first}`.toUpperCase() || 'К';
  }

  get selectedSourceLabel(): string {
    const source = this.customerForm.get('source')?.value;
    return this.sourceOptions.find(option => option.value === source)?.label || 'Источник не указан';
  }
}

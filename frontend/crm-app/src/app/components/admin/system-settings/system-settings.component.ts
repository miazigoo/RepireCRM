// frontend/crm-app/src/app/components/admin/system-settings/system-settings.component.ts
import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatDividerModule } from '@angular/material/divider';
import { AdminService } from '../../../services/admin.service';

interface SystemSettings {
  general: {
    app_name: string;
    app_version: string;
    company_name: string;
    company_address: string;
    company_phone: string;
    company_email: string;
  };
  notifications: {
    email_enabled: boolean;
    sms_enabled: boolean;
    push_enabled: boolean;
    order_status_notifications: boolean;
    daily_reports: boolean;
  };
  security: {
    password_min_length: number;
    password_require_uppercase: boolean;
    password_require_lowercase: boolean;
    password_require_numbers: boolean;
    password_require_symbols: boolean;
    session_timeout_minutes: number;
    max_login_attempts: number;
  };
  backup: {
    auto_backup_enabled: boolean;
    backup_frequency_hours: number;
    backup_retention_days: number;
    backup_location: string;
  };
}

@Component({
  selector: 'app-system-settings',
  standalone: true,
  imports: [
    NgIf, ReactiveFormsModule,
    MatCardModule, MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatIconModule, MatSlideToggleModule,
    MatProgressSpinnerModule, MatSnackBarModule, MatTabsModule, MatDividerModule
  ],
  templateUrl: './system-settings.component.html',
  styleUrl: './system-settings.component.css'
})
export class SystemSettingsComponent implements OnInit {
  generalForm!: FormGroup;
  notificationsForm!: FormGroup;
  securityForm!: FormGroup;
  backupForm!: FormGroup;
  
  loading = false;
  settings: SystemSettings | null = null;

  constructor(
    private fb: FormBuilder,
    private adminService: AdminService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.initializeForms();
    this.loadSettings();
  }

  private initializeForms(): void {
    this.generalForm = this.fb.group({
      app_name: ['Repair CRM', Validators.required],
      app_version: ['1.0.0', Validators.required],
      company_name: ['', Validators.required],
      company_address: [''],
      company_phone: [''],
      company_email: ['', Validators.email]
    });

    this.notificationsForm = this.fb.group({
      email_enabled: [true],
      sms_enabled: [false],
      push_enabled: [true],
      order_status_notifications: [true],
      daily_reports: [false]
    });

    this.securityForm = this.fb.group({
      password_min_length: [8, [Validators.required, Validators.min(6), Validators.max(20)]],
      password_require_uppercase: [true],
      password_require_lowercase: [true],
      password_require_numbers: [true],
      password_require_symbols: [false],
      session_timeout_minutes: [480, [Validators.required, Validators.min(30)]],
      max_login_attempts: [5, [Validators.required, Validators.min(3), Validators.max(10)]]
    });

    this.backupForm = this.fb.group({
      auto_backup_enabled: [true],
      backup_frequency_hours: [24, [Validators.required, Validators.min(1)]],
      backup_retention_days: [30, [Validators.required, Validators.min(7)]],
      backup_location: ['/backups/', Validators.required]
    });
  }

  private loadSettings(): void {
    this.loading = true;
    // В реальном приложении загружаем настройки с сервера
    // this.adminService.getSystemSettings().subscribe({...});
    
    // Пока используем мок-данные
    setTimeout(() => {
      this.settings = {
        general: {
          app_name: 'Repair CRM',
          app_version: '1.0.0',
          company_name: 'ООО "Ремонт+"',
          company_address: 'г. Москва, ул. Примерная, д. 123',
          company_phone: '+7 (495) 123-45-67',
          company_email: 'info@repair-plus.ru'
        },
        notifications: {
          email_enabled: true,
          sms_enabled: false,
          push_enabled: true,
          order_status_notifications: true,
          daily_reports: false
        },
        security: {
          password_min_length: 8,
          password_require_uppercase: true,
          password_require_lowercase: true,
          password_require_numbers: true,
          password_require_symbols: false,
          session_timeout_minutes: 480,
          max_login_attempts: 5
        },
        backup: {
          auto_backup_enabled: true,
          backup_frequency_hours: 24,
          backup_retention_days: 30,
          backup_location: '/backups/'
        }
      };

      this.populateForms();
      this.loading = false;
    }, 1000);
  }

  private populateForms(): void {
    if (this.settings) {
      this.generalForm.patchValue(this.settings.general);
      this.notificationsForm.patchValue(this.settings.notifications);
      this.securityForm.patchValue(this.settings.security);
      this.backupForm.patchValue(this.settings.backup);
    }
  }

  saveGeneralSettings(): void {
    if (this.generalForm.valid) {
      this.loading = true;
      // В реальном приложении отправляем данные на сервер
      setTimeout(() => {
        this.snackBar.open('Общие настройки сохранены', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }, 1000);
    }
  }

  saveNotificationSettings(): void {
    if (this.notificationsForm.valid) {
      this.loading = true;
      setTimeout(() => {
        this.snackBar.open('Настройки уведомлений сохранены', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }, 1000);
    }
  }

  saveSecuritySettings(): void {
    if (this.securityForm.valid) {
      this.loading = true;
      setTimeout(() => {
        this.snackBar.open('Настройки безопасности сохранены', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }, 1000);
    }
  }

  saveBackupSettings(): void {
    if (this.backupForm.valid) {
      this.loading = true;
      setTimeout(() => {
        this.snackBar.open('Настройки резервного копирования сохранены', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }, 1000);
    }
  }

  testEmailSettings(): void {
    this.loading = true;
    setTimeout(() => {
      this.snackBar.open('Тестовое письмо отправлено', 'Закрыть', { duration: 3000 });
      this.loading = false;
    }, 2000);
  }

  testSMSSettings(): void {
    this.loading = true;
    setTimeout(() => {
      this.snackBar.open('Тестовое SMS отправлено', 'Закрыть', { duration: 3000 });
      this.loading = false;
    }, 2000);
  }

  createBackupNow(): void {
    this.loading = true;
    setTimeout(() => {
      this.snackBar.open('Резервная копия создана успешно', 'Закрыть', { duration: 3000 });
      this.loading = false;
    }, 3000);
  }

  getFieldError(form: FormGroup, fieldName: string): string {
    const control = form.get(fieldName);
    if (control?.errors && control.touched) {
      if (control.errors['required']) {
        return 'Поле обязательно для заполнения';
      }
      if (control.errors['email']) {
        return 'Введите корректный email';
      }
      if (control.errors['min']) {
        return `Минимальное значение: ${control.errors['min'].min}`;
      }
      if (control.errors['max']) {
        return `Максимальное значение: ${control.errors['max'].max}`;
      }
    }
    return '';
  }
}

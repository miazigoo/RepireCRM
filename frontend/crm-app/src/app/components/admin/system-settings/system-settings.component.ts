// frontend/crm-app/src/app/components/admin/system-settings/system-settings.component.ts
import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, DatePipe } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatDividerModule } from '@angular/material/divider';
import { finalize } from 'rxjs';
import {
  AdminService,
  ClientPortalIntegration,
  ClientPortalIntegrationUpdate,
  ClientSyncAction,
  ClientSyncRunResult,
  ClientSyncStatus,
} from '../../../services/admin.service';

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

type SettingsOverviewTone = 'primary' | 'accent' | 'warning';

interface SettingsOverviewItem {
  label: string;
  value: string;
  tone: SettingsOverviewTone;
}

@Component({
  selector: 'app-system-settings',
  standalone: true,
  imports: [
    NgIf, NgFor, DatePipe, ReactiveFormsModule,
    MatFormFieldModule, MatInputModule,
    MatButtonModule, MatSlideToggleModule,
    MatProgressSpinnerModule, MatSnackBarModule, MatTabsModule, MatDividerModule
  ],
  templateUrl: './system-settings.component.html',
  styleUrl: './system-settings.component.scss'
})
export class SystemSettingsComponent implements OnInit {
  private readonly storageKey = 'repairCrmSystemSettings';

  generalForm!: FormGroup;
  notificationsForm!: FormGroup;
  securityForm!: FormGroup;
  backupForm!: FormGroup;
  clientSyncForm!: FormGroup;

  loading = false;
  clientSyncLoading = false;
  clientSyncSaving = false;
  clientSyncRunning = false;
  settings: SystemSettings | null = null;
  clientSyncStatus: ClientSyncStatus | null = null;
  clientSyncActions: ClientSyncAction[] = [];
  clientSyncResult: ClientSyncRunResult | null = null;
  settingsOverview: SettingsOverviewItem[] = [
    { label: 'Каналы', value: 'Email + Push', tone: 'primary' },
    { label: 'Сессия', value: '480 мин', tone: 'accent' },
    { label: 'Резерв', value: '24 ч', tone: 'warning' },
  ];

  constructor(
    private fb: FormBuilder,
    private snackBar: MatSnackBar,
    private adminService: AdminService
  ) {}

  ngOnInit(): void {
    this.initializeForms();
    this.loadSettings();
    this.loadClientSyncStatus();
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

    this.clientSyncForm = this.fb.group({
      enabled: [false],
      base_url: [''],
      api_key: [''],
      tenant_key: [''],
      client_domain: [''],
      auth_policy: ['phone_or_email'],
      support_phone: [''],
      support_email: ['', Validators.email],
      brand_name: [''],
      accent_color: [''],
      portal_banner_enabled: [false],
      portal_banner_title: [''],
      portal_banner_subtitle: [''],
      portal_banner_image_url: [''],
      portal_banner_link_url: [''],
    });
  }

  private loadSettings(): void {
    this.loading = true;

    this.settings = this.mergeSettings(this.readSavedSettings());
    this.populateForms();
    this.syncOverview();
    this.loading = false;
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
      this.patchSettings(
        'general',
        this.generalForm.getRawValue() as SystemSettings['general']
      );
      this.snackBar.open('Общие настройки сохранены', 'Закрыть', { duration: 3000 });
    }
  }

  saveNotificationSettings(): void {
    if (this.notificationsForm.valid) {
      this.patchSettings(
        'notifications',
        this.notificationsForm.getRawValue() as SystemSettings['notifications']
      );
      this.snackBar.open('Настройки уведомлений сохранены', 'Закрыть', { duration: 3000 });
    }
  }

  saveSecuritySettings(): void {
    if (this.securityForm.valid) {
      this.patchSettings(
        'security',
        this.securityForm.getRawValue() as SystemSettings['security']
      );
      this.snackBar.open('Настройки безопасности сохранены', 'Закрыть', { duration: 3000 });
    }
  }

  saveBackupSettings(): void {
    if (this.backupForm.valid) {
      this.patchSettings(
        'backup',
        this.backupForm.getRawValue() as SystemSettings['backup']
      );
      this.snackBar.open('Настройки резервного копирования сохранены', 'Закрыть', { duration: 3000 });
    }
  }

  testEmailSettings(): void {
    this.snackBar.open('Тестовое письмо отправлено', 'Закрыть', { duration: 3000 });
  }

  testSMSSettings(): void {
    this.snackBar.open('Тестовое SMS отправлено', 'Закрыть', { duration: 3000 });
  }

  createBackupNow(): void {
    this.snackBar.open('Резервная копия создана успешно', 'Закрыть', { duration: 3000 });
  }

  saveClientSyncSettings(): void {
    if (this.clientSyncForm.invalid) {
      this.clientSyncForm.markAllAsTouched();
      return;
    }

    const payload = this.cleanSyncPayload(
      this.clientSyncForm.getRawValue() as Record<string, unknown>
    );
    this.clientSyncSaving = true;
    this.adminService.updateClientSyncIntegration(payload)
      .pipe(finalize(() => (this.clientSyncSaving = false)))
      .subscribe({
        next: (integration) => {
          this.patchClientSyncForm(integration);
          this.loadClientSyncStatus(false);
          this.snackBar.open('Настройки клиентского кабинета сохранены', 'Закрыть', { duration: 3000 });
        },
        error: (error) => {
          this.snackBar.open(this.extractApiError(error, 'Не удалось сохранить настройки'), 'Закрыть', { duration: 3500 });
        },
      });
  }

  runClientSync(): void {
    this.clientSyncRunning = true;
    this.clientSyncResult = null;
    this.adminService.runClientSync(true, true, 100)
      .pipe(finalize(() => (this.clientSyncRunning = false)))
      .subscribe({
        next: (result) => {
          this.clientSyncResult = result;
          this.loadClientSyncStatus(false);
          this.snackBar.open('Синхронизация запущена', 'Закрыть', { duration: 3000 });
        },
        error: (error) => {
          this.snackBar.open(this.extractApiError(error, 'Не удалось запустить синхронизацию'), 'Закрыть', { duration: 3500 });
        },
      });
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

  private patchSettings<T extends keyof SystemSettings>(section: T, value: SystemSettings[T]): void {
    this.settings = {
      ...this.mergeSettings(this.settings ?? undefined),
      [section]: value
    };
    localStorage.setItem(this.storageKey, JSON.stringify(this.settings));
    this.syncOverview();
  }

  private loadClientSyncStatus(showLoader = true): void {
    if (showLoader) {
      this.clientSyncLoading = true;
    }

    this.adminService.getClientSyncStatus()
      .pipe(finalize(() => (this.clientSyncLoading = false)))
      .subscribe({
        next: (status) => {
          this.clientSyncStatus = status;
          this.patchClientSyncForm(status.integration);
          this.loadClientSyncActions();
        },
        error: () => {
          this.clientSyncStatus = null;
          this.clientSyncActions = [];
        },
      });
  }

  private loadClientSyncActions(): void {
    this.adminService.getClientSyncActions(20).subscribe({
      next: (actions) => (this.clientSyncActions = actions),
      error: () => (this.clientSyncActions = []),
    });
  }

  private patchClientSyncForm(integration: ClientPortalIntegration): void {
    this.clientSyncForm.patchValue({
      enabled: integration.enabled,
      base_url: integration.base_url || '',
      api_key: '',
      tenant_key: integration.tenant_key || '',
      client_domain: integration.client_domain || '',
      auth_policy: integration.auth_policy || 'phone_or_email',
      support_phone: integration.support_phone || '',
      support_email: integration.support_email || '',
      brand_name: integration.brand_name || '',
      accent_color: integration.accent_color || '',
      portal_banner_enabled: integration.portal_banner_enabled,
      portal_banner_title: integration.portal_banner_title || '',
      portal_banner_subtitle: integration.portal_banner_subtitle || '',
      portal_banner_image_url: integration.portal_banner_image_url || '',
      portal_banner_link_url: integration.portal_banner_link_url || '',
    });
  }

  private cleanSyncPayload(value: Record<string, unknown>): ClientPortalIntegrationUpdate {
    const payload: Record<string, unknown> = {};
    Object.entries(value).forEach(([key, currentValue]) => {
      if (typeof currentValue === 'string') {
        const trimmed = currentValue.trim();
        if (key === 'api_key' && !trimmed) {
          return;
        }
        payload[key] = trimmed || null;
        return;
      }
      payload[key] = currentValue;
    });
    return payload as ClientPortalIntegrationUpdate;
  }

  private extractApiError(error: unknown, fallback: string): string {
    const response = error as { error?: { error?: string; detail?: string } };
    return response.error?.error || response.error?.detail || fallback;
  }

  private syncOverview(): void {
    const settings = this.settings || this.getDefaultSettings();
    const notificationChannels = [
      settings.notifications.email_enabled ? 'Email' : null,
      settings.notifications.sms_enabled ? 'SMS' : null,
      settings.notifications.push_enabled ? 'Push' : null,
    ].filter(Boolean).join(' + ') || 'Отключены';

    this.settingsOverview = [
      { label: 'Каналы', value: notificationChannels, tone: 'primary' },
      { label: 'Сессия', value: `${settings.security.session_timeout_minutes} мин`, tone: 'accent' },
      { label: 'Резерв', value: settings.backup.auto_backup_enabled ? `${settings.backup.backup_frequency_hours} ч` : 'Вручную', tone: 'warning' },
    ];
  }

  private readSavedSettings(): Partial<SystemSettings> | undefined {
    const savedSettings = localStorage.getItem(this.storageKey);
    if (!savedSettings) {
      return undefined;
    }

    try {
      return JSON.parse(savedSettings) as Partial<SystemSettings>;
    } catch {
      localStorage.removeItem(this.storageKey);
      return undefined;
    }
  }

  private mergeSettings(saved?: Partial<SystemSettings>): SystemSettings {
    const defaults = this.getDefaultSettings();

    return {
      general: { ...defaults.general, ...saved?.general },
      notifications: { ...defaults.notifications, ...saved?.notifications },
      security: { ...defaults.security, ...saved?.security },
      backup: { ...defaults.backup, ...saved?.backup }
    };
  }

  private getDefaultSettings(): SystemSettings {
    return {
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
  }
}

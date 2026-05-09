import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { AdminService, ClientSyncStatus } from '../../../services/admin.service';
import { SystemSettingsComponent } from './system-settings.component';

describe('SystemSettingsComponent', () => {
  let fixture: ComponentFixture<SystemSettingsComponent>;
  let component: SystemSettingsComponent;
  let adminService: jasmine.SpyObj<AdminService>;

  const storageKey = 'repairCrmSystemSettings';
  const clientSyncStatus: ClientSyncStatus = {
    integration: {
      id: 1,
      organization_id: 1,
      organization_name: 'Repair',
      enabled: false,
      configured: false,
      tenant_key: 'org-1',
      auth_policy: 'phone_or_email',
      portal_banner_enabled: false,
      api_key_configured: false,
    },
    order_states: {},
    actions: {},
  };

  beforeEach(async () => {
    localStorage.clear();
    adminService = jasmine.createSpyObj<AdminService>('AdminService', [
      'getClientSyncStatus',
      'getClientSyncActions',
      'updateClientSyncIntegration',
      'runClientSync',
    ]);
    adminService.getClientSyncStatus.and.returnValue(of(clientSyncStatus));
    adminService.getClientSyncActions.and.returnValue(of([]));
    adminService.updateClientSyncIntegration.and.returnValue(of(clientSyncStatus.integration));
    adminService.runClientSync.and.returnValue(
      of({ pushed: 0, skipped: 0, pulled: 0, applied: 0, errors: 0 })
    );

    await TestBed.configureTestingModule({
      imports: [SystemSettingsComponent],
      providers: [provideNoopAnimations(), { provide: AdminService, useValue: adminService }],
    }).compileComponents();
  });

  afterEach(() => {
    localStorage.clear();
  });

  function createComponent(): void {
    fixture = TestBed.createComponent(SystemSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('renders redesigned settings shell and tab sections', () => {
    createComponent();

    const element: HTMLElement = fixture.nativeElement;

    expect(element.querySelector('.settings-shell')).not.toBeNull();
    expect(element.querySelectorAll('.hero-pulse span').length).toBe(3);
    expect(element.textContent).toContain('Настройки');
    expect(element.textContent).toContain('Общие');
    expect(element.textContent).toContain('Уведомления');
    expect(element.textContent).toContain('Безопасность');
    expect(element.textContent).toContain('Клиентский кабинет');
    expect(element.textContent).toContain('Резервное копирование');
  });

  it('persists general settings locally and updates overview', () => {
    createComponent();

    component.generalForm.patchValue({
      company_name: 'Тестовая мастерская',
      company_email: 'service@example.com',
    });
    component.saveGeneralSettings();

    const savedSettings = JSON.parse(localStorage.getItem(storageKey) || '{}') as {
      general: { company_name: string; company_email: string };
    };

    expect(savedSettings.general.company_name).toBe('Тестовая мастерская');
    expect(savedSettings.general.company_email).toBe('service@example.com');
  });

  it('falls back to defaults when saved settings are corrupted', () => {
    localStorage.setItem(storageKey, '{broken');

    createComponent();

    expect(component.settings?.general.app_name).toBe('Repair CRM');
    expect(localStorage.getItem(storageKey)).toBeNull();
  });
});

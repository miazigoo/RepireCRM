import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { SystemSettingsComponent } from './system-settings.component';

describe('SystemSettingsComponent', () => {
  let fixture: ComponentFixture<SystemSettingsComponent>;
  let component: SystemSettingsComponent;

  const storageKey = 'repairCrmSystemSettings';

  beforeEach(async () => {
    localStorage.clear();

    await TestBed.configureTestingModule({
      imports: [SystemSettingsComponent],
      providers: [provideNoopAnimations()],
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

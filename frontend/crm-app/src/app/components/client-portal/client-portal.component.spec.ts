import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { MatTabGroup } from '@angular/material/tabs';
import { of } from 'rxjs';
import { ClientPortalService } from '../../services/client-portal.service';
import { ClientPortalComponent } from './client-portal.component';

describe('ClientPortalComponent', () => {
  let fixture: ComponentFixture<ClientPortalComponent>;
  let component: ClientPortalComponent;
  let portalService: jasmine.SpyObj<ClientPortalService>;

  beforeEach(async () => {
    portalService = jasmine.createSpyObj<ClientPortalService>(
      'ClientPortalService',
      [
        'isAuthenticated',
        'me',
        'login',
        'register',
        'trackOrder',
        'orders',
        'createOrder',
        'approveApproval',
        'rejectApproval',
        'logout',
      ],
      { customer$: of(null) }
    );
    portalService.isAuthenticated.and.returnValue(false);

    await TestBed.configureTestingModule({
      imports: [ClientPortalComponent],
      providers: [
        provideNoopAnimations(),
        { provide: ClientPortalService, useValue: portalService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ClientPortalComponent);
    component = fixture.componentInstance;
  });

  it('switches auth tab when the user selects registration', () => {
    fixture.detectChanges();
    const tabGroup = fixture.debugElement.query(By.directive(MatTabGroup))
      .componentInstance as MatTabGroup;

    tabGroup.selectedIndexChange.emit(1);
    fixture.detectChanges();

    expect(component.authMode).toBe('register');
    expect(tabGroup.selectedIndex).toBe(1);
  });

  it('switches back to login tab without keeping stale messages', () => {
    component.error = 'Ошибка';
    component.success = 'Готово';
    fixture.detectChanges();

    const tabGroup = fixture.debugElement.query(By.directive(MatTabGroup))
      .componentInstance as MatTabGroup;
    tabGroup.selectedIndexChange.emit(1);
    tabGroup.selectedIndexChange.emit(0);
    fixture.detectChanges();

    expect(component.authMode).toBe('login');
    expect(component.error).toBe('');
    expect(component.success).toBe('');
  });
});

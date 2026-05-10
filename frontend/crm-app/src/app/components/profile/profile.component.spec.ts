import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { Store } from '@ngrx/store';
import { of } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { selectCurrentShop, selectCurrentUser } from '../../store/auth/auth.selectors';
import { AvatarCropDialogComponent } from './avatar-crop-dialog/avatar-crop-dialog.component';
import { ProfileComponent } from './profile.component';

describe('ProfileComponent', () => {
  let fixture: ComponentFixture<ProfileComponent>;
  let component: ProfileComponent;
  let authService: jasmine.SpyObj<AuthService>;
  let dialog: jasmine.SpyObj<MatDialog>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let store: jasmine.SpyObj<Store>;

  const shop = {
    id: 1,
    name: 'Ремонт+ Москва Центр',
    code: 'MSK01',
    is_active: true,
    timezone: 'Europe/Moscow',
    currency: 'RUB',
  } as any;

  const user = {
    id: 1,
    username: 'b00bs',
    first_name: 'Тест',
    last_name: 'Пользователь',
    middle_name: 'CRM',
    email: 'b00bs@example.com',
    phone: '+79991234567',
    is_director: true,
    is_active: true,
    current_shop: shop,
    role: { id: 1, name: 'Директор', code: 'director' },
  } as any;

  beforeEach(async () => {
    authService = jasmine.createSpyObj<AuthService>('AuthService', [
      'getCurrentUser',
      'changePassword',
      'updateProfile',
      'updateAvatar',
      'getProfileStatistics',
    ]);
    authService.getCurrentUser.and.returnValue(of(user));
    authService.changePassword.and.returnValue(of({ message: 'Пароль успешно изменен' }));
    authService.updateProfile.and.returnValue(of(user));
    authService.updateAvatar.and.returnValue(of(user));
    authService.getProfileStatistics.and.returnValue(of({
      orders: { completed: 2, services_revenue: 1500 },
      sales: { revenue: 3000 },
      tasks: { paid_amount: 500 },
      compensation: { estimated_salary: 2000 },
    }));

    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    dialog.open.and.returnValue({ afterClosed: () => of(null) } as any);

    store = jasmine.createSpyObj<Store>('Store', ['select']);
    store.select.and.callFake((selector: any) => {
      if (selector === selectCurrentUser) {
        return of(user);
      }

      if (selector === selectCurrentShop) {
        return of(shop);
      }

      return of(null);
    });

    await TestBed.configureTestingModule({
      imports: [ProfileComponent],
      providers: [
        provideNoopAnimations(),
        { provide: AuthService, useValue: authService },
        { provide: MatDialog, useValue: dialog },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: Store, useValue: store },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ProfileComponent);
    component = fixture.componentInstance;
    (component as any).dialog = dialog;
    (component as any).snackBar = snackBar;
    fixture.detectChanges();
  });

  it('renders current employee profile and access stats', () => {
    const element: HTMLElement = fixture.nativeElement;

    expect(element.querySelector('.profile-shell')).not.toBeNull();
    expect(element.textContent).toContain('Пользователь Тест CRM');
    expect(element.textContent).toContain('b00bs@example.com');
    expect(element.textContent).toContain('Ремонт+ Москва Центр');
    expect(component.profileStats.length).toBe(4);
  });

  it('submits password change through auth API', () => {
    component.passwordForm.patchValue({
      old_password: 'QwsAzx@2000',
      new_password: 'NewPass@2001',
      confirm_password: 'NewPass@2001',
    });

    component.changePassword();

    expect(authService.changePassword).toHaveBeenCalledWith({
      old_password: 'QwsAzx@2000',
      new_password: 'NewPass@2001',
      confirm_password: 'NewPass@2001',
    });
    expect(component.savingPassword).toBeFalse();
    expect(component.passwordForm.get('old_password')?.value).toBeNull();
  });

  it('updates public profile fields through auth API', () => {
    component.profileForm.patchValue({
      profile_status: 'На смене',
      bio: 'Ремонтирую телефоны',
    });

    component.saveProfile();

    expect(authService.updateProfile).toHaveBeenCalledWith(
      jasmine.objectContaining({
        profile_status: 'На смене',
        bio: 'Ремонтирую телефоны',
      }),
    );
  });

  it('uploads a valid avatar through auth API', () => {
    const input = document.createElement('input');
    const file = new File(['avatar'], 'avatar.png', { type: 'image/png' });
    const croppedFile = new File(['cropped'], 'avatar-avatar.jpg', { type: 'image/jpeg' });
    spyOn(URL, 'createObjectURL').and.returnValue('blob:avatar');
    spyOn(URL, 'revokeObjectURL').and.stub();
    dialog.open.and.returnValue({ afterClosed: () => of(croppedFile) } as any);
    Object.defineProperty(input, 'files', { value: [file] });
    input.value = 'avatar.png';

    component.uploadAvatar({ target: input } as any);

    expect(dialog.open).toHaveBeenCalledWith(
      AvatarCropDialogComponent,
      jasmine.objectContaining({
        data: { sourceUrl: 'blob:avatar', fileName: 'avatar.png' },
      }),
    );
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:avatar');
    expect(authService.updateAvatar).toHaveBeenCalledWith(croppedFile);
    expect(component.savingAvatar).toBeFalse();
    expect(input.value).toBe('');
  });

  it('rejects unsupported avatar files before API call', () => {
    const input = document.createElement('input');
    const file = new File(['document'], 'avatar.svg', { type: 'image/svg+xml' });
    Object.defineProperty(input, 'files', { value: [file] });
    input.value = 'avatar.svg';

    component.uploadAvatar({ target: input } as any);

    expect(authService.updateAvatar).not.toHaveBeenCalled();
    expect(snackBar.open).toHaveBeenCalledWith('Загрузите JPG, PNG или WebP', 'Закрыть', { duration: 4000 });
    expect(input.value).toBe('');
  });

  it('keeps mismatched password form invalid', () => {
    component.passwordForm.patchValue({
      old_password: 'QwsAzx@2000',
      new_password: 'NewPass@2001',
      confirm_password: 'OtherPass@2001',
    });

    component.changePassword();

    expect(component.passwordForm.invalid).toBeTrue();
    expect(authService.changePassword).not.toHaveBeenCalled();
  });
});

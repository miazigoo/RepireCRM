import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { AbstractControl, FormBuilder, FormGroup, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { Shop, User } from '../../core/models/models';
import { AppState } from '../../store/app.state';
import { selectCurrentShop, selectCurrentUser } from '../../store/auth/auth.selectors';

interface ProfileStat {
  label: string;
  value: string;
  icon: string;
}

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatDividerModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss'
})
export class ProfileComponent implements OnInit {
  currentUser$: Observable<User | null>;
  currentShop$: Observable<Shop | null>;

  currentUser: User | null = null;
  currentShop: Shop | null = null;
  loadingProfile = false;
  savingPassword = false;
  hideOldPassword = true;
  hideNewPassword = true;
  hideConfirmPassword = true;

  passwordForm: FormGroup;
  profileForm: FormGroup;
  profileStats: ProfileStat[] = [];
  performanceStats: any = null;
  savingProfile = false;

  constructor(
    private fb: FormBuilder,
    private store: Store<AppState>,
    private authService: AuthService,
    private snackBar: MatSnackBar
  ) {
    this.currentUser$ = this.store.select(selectCurrentUser);
    this.currentShop$ = this.store.select(selectCurrentShop);
    this.passwordForm = this.fb.group({
      old_password: ['', Validators.required],
      new_password: ['', [Validators.required, Validators.minLength(8)]],
      confirm_password: ['', Validators.required],
    }, { validators: this.passwordsMatchValidator });
    this.profileForm = this.fb.group({
      first_name: [''],
      last_name: [''],
      middle_name: [''],
      email: ['', Validators.email],
      phone: [''],
      profile_status: [''],
      bio: [''],
    });
  }

  ngOnInit(): void {
    this.currentUser$.subscribe(user => {
      this.currentUser = user;
      if (user) {
        this.patchProfileForm(user);
      }
      this.syncProfileStats();
    });

    this.currentShop$.subscribe(shop => {
      this.currentShop = shop;
      this.syncProfileStats();
    });

    this.refreshProfile();
  }

  refreshProfile(): void {
    this.loadingProfile = true;
    this.authService.getCurrentUser().subscribe({
      next: user => {
        this.currentUser = user;
        this.currentShop = user.current_shop || this.currentShop;
        this.patchProfileForm(user);
        this.syncProfileStats();
        this.loadPerformanceStats();
        this.loadingProfile = false;
      },
      error: () => {
        this.loadingProfile = false;
        this.snackBar.open('Не удалось обновить профиль', 'Закрыть', { duration: 4000 });
      }
    });
  }

  changePassword(): void {
    if (this.passwordForm.invalid) {
      this.passwordForm.markAllAsTouched();
      return;
    }

    this.savingPassword = true;
    this.authService.changePassword(this.passwordForm.getRawValue()).subscribe({
      next: response => {
        this.savingPassword = false;
        this.passwordForm.reset();
        this.snackBar.open(response.message || 'Пароль обновлен', 'Закрыть', { duration: 3500 });
      },
      error: error => {
        this.savingPassword = false;
        this.snackBar.open(this.extractErrorMessage(error), 'Закрыть', { duration: 5000 });
      }
    });
  }

  saveProfile(): void {
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }

    this.savingProfile = true;
    this.authService.updateProfile(this.profileForm.getRawValue()).subscribe({
      next: user => {
        this.currentUser = user;
        this.patchProfileForm(user);
        this.syncProfileStats();
        this.savingProfile = false;
        this.snackBar.open('Профиль обновлен', 'Закрыть', { duration: 3000 });
      },
      error: error => {
        this.savingProfile = false;
        this.snackBar.open(this.extractErrorMessage(error), 'Закрыть', { duration: 5000 });
      }
    });
  }

  uploadAvatar(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }

    this.authService.updateAvatar(file).subscribe({
      next: user => {
        this.currentUser = user;
        this.snackBar.open('Аватар обновлен', 'Закрыть', { duration: 3000 });
      },
      error: error => this.snackBar.open(this.extractErrorMessage(error), 'Закрыть', { duration: 5000 }),
    });
  }

  get displayName(): string {
    if (!this.currentUser) {
      return 'Пользователь';
    }

    const fullName = [
      this.currentUser.last_name,
      this.currentUser.first_name,
      this.currentUser.middle_name,
    ].filter(Boolean).join(' ');

    return fullName || this.currentUser.username;
  }

  get initials(): string {
    const source = [
      this.currentUser?.first_name?.charAt(0),
      this.currentUser?.last_name?.charAt(0),
    ].filter(Boolean).join('');

    return source || this.currentUser?.username?.charAt(0)?.toUpperCase() || 'U';
  }

  get roleName(): string {
    if (this.currentUser?.is_director) {
      return 'Директор';
    }

    return this.currentUser?.role?.name || 'Роль не назначена';
  }

  getFieldError(fieldName: string): string {
    const control = this.passwordForm.get(fieldName);

    if (!control?.touched) {
      return '';
    }

    if (fieldName === 'confirm_password' && this.passwordForm.errors?.['passwordMismatch']) {
      return 'Пароли не совпадают';
    }

    if (!control.errors) {
      return '';
    }

    if (control.errors['required']) {
      return 'Поле обязательно';
    }

    if (control.errors['minlength']) {
      return `Минимум ${control.errors['minlength'].requiredLength} символов`;
    }

    return 'Проверьте значение';
  }

  private passwordsMatchValidator(control: AbstractControl): ValidationErrors | null {
    const newPassword = control.get('new_password')?.value;
    const confirmPasswordControl = control.get('confirm_password');
    const confirmPassword = confirmPasswordControl?.value;

    if (!newPassword || !confirmPassword) {
      return null;
    }

    if (newPassword !== confirmPassword) {
      return { passwordMismatch: true };
    }

    return null;
  }

  private syncProfileStats(): void {
    this.profileStats = [
      {
        label: 'Логин',
        value: this.currentUser?.username || 'Не загружен',
        icon: 'badge',
      },
      {
        label: 'Роль',
        value: this.roleName,
        icon: 'admin_panel_settings',
      },
      {
        label: 'Филиал',
        value: this.currentShop?.name || this.currentUser?.current_shop?.name || 'Не выбран',
        icon: 'storefront',
      },
      {
        label: 'Статус',
        value: this.currentUser?.profile_status || (this.currentUser?.is_active ? 'Активен' : 'Отключен'),
        icon: this.currentUser?.is_active ? 'verified_user' : 'block',
      },
    ];
  }

  private patchProfileForm(user: User): void {
    this.profileForm.patchValue({
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      middle_name: user.middle_name || '',
      email: user.email || '',
      phone: user.phone || '',
      profile_status: user.profile_status || '',
      bio: user.bio || '',
    }, { emitEvent: false });
  }

  private loadPerformanceStats(): void {
    this.authService.getProfileStatistics({ period: 'month' }).subscribe({
      next: stats => {
        this.performanceStats = stats;
      },
      error: () => {
        this.performanceStats = null;
      }
    });
  }

  private extractErrorMessage(error: any): string {
    return (
      error?.error?.error ||
      error?.error?.detail ||
      error?.message ||
      'Не удалось изменить пароль'
    );
  }
}

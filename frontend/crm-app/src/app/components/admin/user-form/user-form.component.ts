// frontend/crm-app/src/app/components/admin/user-form/user-form.component.ts
import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { AdminService, UserCreateRequest, UserUpdateRequest } from '../../../services/admin.service';
import { User, Role, Shop } from '../../../core/models/models';

@Component({
  selector: 'app-user-form',
  standalone: true,
  imports: [
    NgIf, NgFor, ReactiveFormsModule,
    MatCardModule, MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatIconModule, MatCheckboxModule, MatChipsModule,
    MatProgressSpinnerModule, MatSnackBarModule
  ],
  templateUrl: './user-form.component.html',
  styleUrl: './user-form.component.css'
})
export class UserFormComponent implements OnInit {
  userForm: FormGroup;
  isEditMode = false;
  userId: number | null = null;
  loading = false;
  
  roles: Role[] = [];
  shops: Shop[] = [];
  selectedShops: Shop[] = [];

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private adminService: AdminService,
    private snackBar: MatSnackBar
  ) {
    this.userForm = this.fb.group({
      username: ['', [Validators.required, Validators.minLength(3)]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirm_password: ['', Validators.required],
      first_name: ['', [Validators.required, Validators.maxLength(50)]],
      last_name: ['', [Validators.required, Validators.maxLength(50)]],
      middle_name: ['', Validators.maxLength(50)],
      email: ['', [Validators.required, Validators.email]],
      phone: ['', Validators.pattern(/^\+?[1-9]\d{1,14}$/)],
      role_id: [''],
      is_director: [false],
      shop_ids: [[]],
      is_active: [true]
    }, { validators: this.passwordMatchValidator });
  }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.isEditMode = true;
        this.userId = +params['id'];
        this.userForm.get('password')?.clearValidators();
        this.userForm.get('confirm_password')?.clearValidators();
        this.userForm.get('password')?.updateValueAndValidity();
        this.userForm.get('confirm_password')?.updateValueAndValidity();
        this.loadUser(this.userId);
      }
    });

    this.loadRoles();
    this.loadShops();
  }

  private passwordMatchValidator(form: FormGroup) {
    const password = form.get('password');
    const confirmPassword = form.get('confirm_password');
    
    if (password && confirmPassword && password.value !== confirmPassword.value) {
      confirmPassword.setErrors({ passwordMismatch: true });
      return { passwordMismatch: true };
    }
    return null;
  }

  private loadUser(id: number): void {
    this.loading = true;
    this.adminService.getUser(id).subscribe({
      next: (user) => {
        this.populateForm(user);
        this.loading = false;
      },
      error: (error) => {
        this.snackBar.open('Ошибка загрузки пользователя', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  private populateForm(user: User): void {
    this.userForm.patchValue({
      username: user.username,
      first_name: user.first_name,
      last_name: user.last_name,
      middle_name: user.middle_name,
      email: user.email,
      phone: user.phone,
      role_id: user.role?.id,
      is_director: user.is_director,
      is_active: user.is_active
    });

    // Set selected shops
    if ((user as any).shops) {
      this.selectedShops = (user as any).shops;
      this.userForm.patchValue({
        shop_ids: this.selectedShops.map(shop => shop.id)
      });
    }
  }

  private loadRoles(): void {
    this.adminService.getRoles().subscribe({
      next: (roles) => {
        this.roles = roles;
      },
      error: (error) => {
        console.error('Error loading roles:', error);
      }
    });
  }

  private loadShops(): void {
    this.adminService.getShops().subscribe({
      next: (shops) => {
        this.shops = shops;
      },
      error: (error) => {
        console.error('Error loading shops:', error);
      }
    });
  }

  onShopSelectionChange(selectedShopIds: number[]): void {
    this.selectedShops = this.shops.filter(shop => selectedShopIds.includes(shop.id));
    this.userForm.patchValue({ shop_ids: selectedShopIds });
  }

  removeShop(shop: Shop): void {
    this.selectedShops = this.selectedShops.filter(s => s.id !== shop.id);
    this.userForm.patchValue({
      shop_ids: this.selectedShops.map(s => s.id)
    });
  }

  onSubmit(): void {
    if (this.userForm.valid) {
      this.loading = true;
      
      const formData = this.userForm.value;
      
      if (this.isEditMode) {
        const updateData: UserUpdateRequest = {
          first_name: formData.first_name,
          last_name: formData.last_name,
          middle_name: formData.middle_name,
          email: formData.email,
          phone: formData.phone,
          role_id: formData.role_id,
          is_director: formData.is_director,
          shop_ids: formData.shop_ids,
          is_active: formData.is_active
        };

        this.adminService.updateUser(this.userId!, updateData).subscribe({
          next: (user) => {
            this.snackBar.open('Пользователь обновлен', 'Закрыть', { duration: 3000 });
            this.router.navigate(['/admin/users']);
          },
          error: (error) => {
            this.handleError(error);
          }
        });
      } else {
        const createData: UserCreateRequest = {
          username: formData.username,
          password: formData.password,
          first_name: formData.first_name,
          last_name: formData.last_name,
          middle_name: formData.middle_name,
          email: formData.email,
          phone: formData.phone,
          role_id: formData.role_id,
          shop_ids: formData.shop_ids,
          is_director: formData.is_director
        };

        this.adminService.createUser(createData).subscribe({
          next: (user) => {
            this.snackBar.open('Пользователь создан', 'Закрыть', { duration: 3000 });
            this.router.navigate(['/admin/users']);
          },
          error: (error) => {
            this.handleError(error);
          }
        });
      }
    } else {
      this.markFormGroupTouched();
    }
  }

  private handleError(error: any): void {
    let errorMessage = 'Ошибка сохранения пользователя';
    
    if (error.error?.error) {
      errorMessage = error.error.error;
    } else if (error.error?.username) {
      errorMessage = 'Пользователь с таким логином уже существует';
    } else if (error.error?.email) {
      errorMessage = 'Пользователь с таким email уже существует';
    }
    
    this.snackBar.open(errorMessage, 'Закрыть', { duration: 5000 });
    this.loading = false;
  }

  private markFormGroupTouched(): void {
    Object.keys(this.userForm.controls).forEach(key => {
      const control = this.userForm.get(key);
      control?.markAsTouched();
    });
  }

  cancel(): void {
    this.router.navigate(['/admin/users']);
  }

  getFieldError(fieldName: string): string {
    const control = this.userForm.get(fieldName);
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
      if (control.errors['minlength']) {
        return `Минимум ${control.errors['minlength'].requiredLength} символов`;
      }
      if (control.errors['maxlength']) {
        return `Максимум ${control.errors['maxlength'].requiredLength} символов`;
      }
      if (control.errors['passwordMismatch']) {
        return 'Пароли не совпадают';
      }
    }
    return '';
  }
}

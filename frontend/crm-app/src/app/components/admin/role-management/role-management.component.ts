// frontend/crm-app/src/app/components/admin/role-management/role-management.component.ts
import { Component, OnInit, ViewChild } from '@angular/core';
import { NgIf, NgFor } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator, MatPaginatorIntl } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDividerModule } from '@angular/material/divider';
import { AdminService } from '../../../services/admin.service';
import { Role, Permission } from '../../../core/models/models';
import { RussianPaginatorIntl } from '../../../core/i18n/russian-paginator-intl';

interface PermissionsByCategory {
  [category: string]: Permission[];
}

@Component({
  selector: 'app-role-management',
  standalone: true,
  imports: [
    NgIf,
    NgFor,
    ReactiveFormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatMenuModule,
    MatChipsModule,
    MatSnackBarModule,
    MatCheckboxModule,
    MatExpansionModule,
    MatDividerModule,
  ],
  templateUrl: './role-management.component.html',
  styleUrl: './role-management.component.css',
  providers: [{ provide: MatPaginatorIntl, useClass: RussianPaginatorIntl }],
})
export class RoleManagementComponent implements OnInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  displayedColumns: string[] = ['name', 'code', 'description', 'permissions_count', 'actions'];

  dataSource = new MatTableDataSource<Role>();
  loading = false;
  showForm = false;
  editingRole: Role | null = null;

  roleForm: FormGroup;
  permissions: Permission[] = [];
  permissionsByCategory: PermissionsByCategory = {};
  selectedPermissions: Set<number> = new Set();

  categoryOrder = [
    'orders',
    'customers',
    'inventory',
    'reports',
    'tasks',
    'finance',
    'settings',
    'users',
  ];

  categoryLabels: { [key: string]: string } = {
    orders: 'Заказы',
    customers: 'Клиенты',
    inventory: 'Склад',
    reports: 'Отчеты',
    tasks: 'Задачи',
    finance: 'Финансы',
    settings: 'Настройки',
    users: 'Пользователи и доступ',
  };

  categoryDescriptions: { [key: string]: string } = {
    orders: 'Приемка, ремонт, выдача и управление статусами заказов.',
    customers: 'Просмотр и ведение клиентской базы выбранного филиала.',
    inventory: 'Товары, остатки, закупки, продажи и складские операции.',
    reports: 'Дашборды, финансовые отчеты, аналитика и экспорт.',
    tasks: 'Назначение и контроль задач по сотрудникам, ролям и филиалам.',
    finance: 'Платежи, оплаты заказов и розничных продаж.',
    settings: 'Филиалы, настройки магазина и параметры системы.',
    users: 'Сотрудники, роли, права и привязка пользователей к филиалам.',
  };

  constructor(
    private adminService: AdminService,
    private fb: FormBuilder,
    private snackBar: MatSnackBar,
  ) {
    this.roleForm = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(50)]],
      code: ['', [Validators.required, Validators.maxLength(20), Validators.pattern(/^[a-z_]+$/)]],
      description: ['', Validators.maxLength(200)],
    });
  }

  ngOnInit(): void {
    this.loadRoles();
    this.loadPermissions();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  private loadRoles(): void {
    this.loading = true;
    this.adminService.getRoles().subscribe({
      next: (roles) => {
        this.dataSource.data = roles;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading roles:', error);
        this.snackBar.open('Ошибка загрузки ролей', 'Закрыть', { duration: 3000 });
        this.loading = false;
      },
    });
  }

  private loadPermissions(): void {
    this.adminService.getPermissions().subscribe({
      next: (permissions) => {
        this.permissions = permissions;
        this.groupPermissionsByCategory();
      },
      error: (error) => {
        console.error('Error loading permissions:', error);
      },
    });
  }

  private groupPermissionsByCategory(): void {
    this.permissionsByCategory = this.permissions.reduce((acc, permission) => {
      if (!acc[permission.category]) {
        acc[permission.category] = [];
      }
      acc[permission.category].push(permission);
      return acc;
    }, {} as PermissionsByCategory);

    Object.values(this.permissionsByCategory).forEach((categoryPermissions) => {
      categoryPermissions.sort((first, second) => first.name.localeCompare(second.name, 'ru'));
    });
  }

  showCreateForm(): void {
    this.showForm = true;
    this.editingRole = null;
    this.selectedPermissions.clear();
    this.roleForm.reset();
  }

  editRole(role: Role): void {
    this.showForm = true;
    this.editingRole = role;
    this.roleForm.patchValue({
      name: role.name,
      code: role.code,
      description: role.description,
    });

    // Load role permissions
    this.adminService.getRole(role.id).subscribe({
      next: (fullRole) => {
        this.selectedPermissions.clear();
        if (fullRole.permissions) {
          fullRole.permissions.forEach((permission: Permission) => {
            this.selectedPermissions.add(permission.id);
          });
        }
      },
      error: (error) => {
        console.error('Error loading role permissions:', error);
      },
    });
  }

  cancelForm(): void {
    this.showForm = false;
    this.editingRole = null;
    this.selectedPermissions.clear();
    this.roleForm.reset();
  }

  onSubmit(): void {
    if (this.roleForm.valid) {
      this.loading = true;
      const formData = {
        ...this.roleForm.value,
        permission_ids: Array.from(this.selectedPermissions),
      };

      const request = this.editingRole
        ? this.adminService.updateRole(this.editingRole.id, formData)
        : this.adminService.createRole(formData);

      request.subscribe({
        next: (role) => {
          const message = this.editingRole ? 'Роль обновлена' : 'Роль создана';
          this.snackBar.open(message, 'Закрыть', { duration: 3000 });
          this.cancelForm();
          this.loadRoles();
        },
        error: (error) => {
          const errorMessage = error.error?.error || 'Ошибка сохранения роли';
          this.snackBar.open(errorMessage, 'Закрыть', { duration: 5000 });
          this.loading = false;
        },
      });
    } else {
      this.markFormGroupTouched();
    }
  }

  deleteRole(role: Role): void {
    if (
      confirm(`Удалить роль "${role.name}"? Пользователи с этой ролью потеряют свои права доступа.`)
    ) {
      this.adminService.deleteRole(role.id).subscribe({
        next: () => {
          this.snackBar.open('Роль удалена', 'Закрыть', { duration: 3000 });
          this.loadRoles();
        },
        error: (error) => {
          const errorMessage = error.error?.error || 'Ошибка удаления роли';
          this.snackBar.open(errorMessage, 'Закрыть', { duration: 5000 });
        },
      });
    }
  }

  togglePermission(permission: Permission): void {
    if (this.selectedPermissions.has(permission.id)) {
      this.selectedPermissions.delete(permission.id);
    } else {
      this.selectedPermissions.add(permission.id);
    }
  }

  isPermissionSelected(permission: Permission): boolean {
    return this.selectedPermissions.has(permission.id);
  }

  selectAllInCategory(category: string): void {
    const categoryPermissions = this.permissionsByCategory[category];
    const allSelected = categoryPermissions.every((p) => this.selectedPermissions.has(p.id));

    if (allSelected) {
      // Deselect all in category
      categoryPermissions.forEach((p) => this.selectedPermissions.delete(p.id));
    } else {
      // Select all in category
      categoryPermissions.forEach((p) => this.selectedPermissions.add(p.id));
    }
  }

  isCategoryFullySelected(category: string): boolean {
    const categoryPermissions = this.permissionsByCategory[category];
    return categoryPermissions.every((p) => this.selectedPermissions.has(p.id));
  }

  isCategoryPartiallySelected(category: string): boolean {
    const categoryPermissions = this.permissionsByCategory[category];
    const selectedCount = categoryPermissions.filter((p) =>
      this.selectedPermissions.has(p.id),
    ).length;
    return selectedCount > 0 && selectedCount < categoryPermissions.length;
  }

  private markFormGroupTouched(): void {
    Object.keys(this.roleForm.controls).forEach((key) => {
      const control = this.roleForm.get(key);
      control?.markAsTouched();
    });
  }

  getFieldError(fieldName: string): string {
    const control = this.roleForm.get(fieldName);
    if (control?.errors && control.touched) {
      if (control.errors['required']) {
        return 'Поле обязательно для заполнения';
      }
      if (control.errors['pattern']) {
        return 'Код должен содержать только строчные буквы и подчеркивания';
      }
      if (control.errors['maxlength']) {
        return `Максимум ${control.errors['maxlength'].requiredLength} символов`;
      }
    }
    return '';
  }

  getCategoryLabel(category: string): string {
    return this.categoryLabels[category] || category;
  }

  getCategoryDescription(category: string): string {
    return this.categoryDescriptions[category] || 'Разрешения этого раздела.';
  }

  getPermissionsCount(role: Role): number {
    return role.permissions_count || 0;
  }

  getObjectKeys(obj: any): string[] {
    return Object.keys(obj).sort((first, second) => {
      const firstIndex = this.categoryOrder.indexOf(first);
      const secondIndex = this.categoryOrder.indexOf(second);
      if (firstIndex === -1 && secondIndex === -1) {
        return first.localeCompare(second, 'ru');
      }
      if (firstIndex === -1) {
        return 1;
      }
      if (secondIndex === -1) {
        return -1;
      }
      return firstIndex - secondIndex;
    });
  }
}

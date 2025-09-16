// frontend/crm-app/src/app/components/admin/user-management/user-management.component.ts
import { Component, OnInit, ViewChild } from '@angular/core';
import { NgIf, NgFor, DatePipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { AdminService } from '../../../services/admin.service';
import { User, Role, Shop } from '../../../core/models/models';
import { MatDividerModule } from '@angular/material/divider';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [
    NgIf, NgFor, DatePipe, RouterModule, ReactiveFormsModule,
    MatTableModule, MatPaginatorModule, MatSortModule, MatInputModule,
    MatSelectModule, MatButtonModule, MatIconModule, MatCardModule,
    MatProgressSpinnerModule, MatMenuModule, MatChipsModule,
    MatDialogModule, MatSnackBarModule, MatSlideToggleModule, MatDividerModule
  ],
  templateUrl: './user-management.component.html',
  styleUrl: './user-management.component.css'
})
export class UserManagementComponent implements OnInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  displayedColumns: string[] = [
    'name',
    'username',
    'email',
    'role',
    'shops',
    'is_active',
    'last_login',
    'actions'
  ];

  dataSource = new MatTableDataSource<User>();
  filtersForm: FormGroup;
  loading = false;
  
  roles: Role[] = [];
  shops: Shop[] = [];

  constructor(
    private adminService: AdminService,
    private fb: FormBuilder,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {
    this.filtersForm = this.fb.group({
      search: [''],
      role_id: [''],
      shop_id: [''],
      is_active: ['']
    });
  }

  ngOnInit(): void {
    this.loadUsers();
    this.loadRoles();
    this.loadShops();
    this.setupFilters();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  private loadUsers(): void {
    this.loading = true;
    this.adminService.getUsers().subscribe({
      next: (users) => {
        this.dataSource.data = users;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading users:', error);
        this.snackBar.open('Ошибка загрузки пользователей', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }
    });
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

  private setupFilters(): void {
    this.filtersForm.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged()
      )
      .subscribe(() => {
        this.applyFilters();
      });
  }

  private applyFilters(): void {
    const filters = this.filtersForm.value;
    let filteredData = [...this.dataSource.data];

    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      filteredData = filteredData.filter(user =>
        user.first_name.toLowerCase().includes(searchTerm) ||
        user.last_name.toLowerCase().includes(searchTerm) ||
        user.username.toLowerCase().includes(searchTerm) ||
        user.email.toLowerCase().includes(searchTerm)
      );
    }

    if (filters.role_id) {
      filteredData = filteredData.filter(user => user.role?.id === +filters.role_id);
    }

    if (filters.is_active !== '') {
      filteredData = filteredData.filter(user => user.is_active === filters.is_active);
    }

    this.dataSource.data = filteredData;
  }

  clearFilters(): void {
    this.filtersForm.reset();
    this.dataSource.data = [...this.dataSource.data];
  }

  toggleUserStatus(user: User): void {
    const newStatus = !user.is_active;
    this.adminService.updateUser(user.id, { is_active: newStatus }).subscribe({
      next: (updatedUser) => {
        user.is_active = updatedUser.is_active;
        const statusText = newStatus ? 'активирован' : 'деактивирован';
        this.snackBar.open(`Пользователь ${statusText}`, 'Закрыть', { duration: 3000 });
      },
      error: (error) => {
        this.snackBar.open('Ошибка изменения статуса пользователя', 'Закрыть', { duration: 3000 });
      }
    });
  }

  resetPassword(user: User): void {
    const newPassword = this.generateRandomPassword();
    if (confirm(`Сбросить пароль для пользователя ${user.username}?\nНовый пароль: ${newPassword}`)) {
      this.adminService.resetUserPassword(user.id, newPassword).subscribe({
        next: () => {
          this.snackBar.open('Пароль сброшен', 'Закрыть', { duration: 3000 });
        },
        error: (error) => {
          this.snackBar.open('Ошибка сброса пароля', 'Закрыть', { duration: 3000 });
        }
      });
    }
  }

  deleteUser(user: User): void {
    if (confirm(`Удалить пользователя ${user.first_name} ${user.last_name}?`)) {
      this.adminService.deleteUser(user.id).subscribe({
        next: () => {
          this.snackBar.open('Пользователь удален', 'Закрыть', { duration: 3000 });
          this.loadUsers();
        },
        error: (error) => {
          this.snackBar.open('Ошибка удаления пользователя', 'Закрыть', { duration: 3000 });
        }
      });
    }
  }

  private generateRandomPassword(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let password = '';
    for (let i = 0; i < 8; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return password;
  }

  getRoleName(user: User): string {
    return user.role?.name || 'Не назначена';
  }

  getShopsNames(user: User): string {
    // Assuming user has shops property
    return (user as any).shops?.map((shop: Shop) => shop.name).join(', ') || 'Нет доступа';
  }
}

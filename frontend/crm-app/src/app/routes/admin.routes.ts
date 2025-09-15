// frontend/crm-app/src/app/routers/admin.routes.ts
import { Routes } from '@angular/router';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('../components/admin/admin-dashboard/admin-dashboard.component').then(m => m.AdminDashboardComponent)
  },
  {
    path: 'users',
    loadComponent: () => import('../components/admin/user-management/user-management.component').then(m => m.UserManagementComponent)
  },
  {
    path: 'users/new',
    loadComponent: () => import('../components/admin/user-form/user-form.component').then(m => m.UserFormComponent)
  },
  {
    path: 'users/:id/edit',
    loadComponent: () => import('../components/admin/user-form/user-form.component').then(m => m.UserFormComponent)
  },
  {
    path: 'shops',
    loadComponent: () => import('../components/admin/shop-management/shop-management.component').then(m => m.ShopManagementComponent)
  },
  {
    path: 'roles',
    loadComponent: () => import('../components/admin/role-management/role-management.component').then(m => m.RoleManagementComponent)
  },
  {
    path: 'settings',
    loadComponent: () => import('../components/admin/system-settings/system-settings.component').then(m => m.SystemSettingsComponent)
  }
];

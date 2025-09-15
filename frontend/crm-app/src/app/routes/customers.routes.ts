import { Routes } from '@angular/router';

export const CUSTOMERS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./customers-list/customers-list.component').then(m => m.CustomersListComponent)
  },
  {
    path: 'new',
    loadComponent: () => import('./customer-form/customer-form.component').then(m => m.CustomerFormComponent)
  },
  {
    path: ':id',
    loadComponent: () => import('./customer-detail/customer-detail.component').then(m => m.CustomerDetailComponent)
  },
  {
    path: ':id/edit',
    loadComponent: () => import('./customer-form/customer-form.component').then(m => m.CustomerFormComponent)
  }
];

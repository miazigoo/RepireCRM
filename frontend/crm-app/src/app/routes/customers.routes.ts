import { Routes } from '@angular/router';

export const CUSTOMERS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('../components/customers/customers-list/customers-list.component').then(m => m.CustomersListComponent)
  },
  {
    path: 'new',
    loadComponent: () => import('../components/customers/customer-form/customer-form.component').then(m => m.CustomerFormComponent)
  },
  {
    path: ':id',
    loadComponent: () => import('../components/customers/customer-detail/customer-detail.component').then(m => m.CustomerDetailComponent)
  },
  {
    path: ':id/edit',
    loadComponent: () => import('../components/customers/customer-form/customer-form.component').then(m => m.CustomerFormComponent)
  }
];

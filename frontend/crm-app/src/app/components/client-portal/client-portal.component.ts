import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { finalize } from 'rxjs';
import {
  ClientPortalService,
  PortalCustomer,
  PortalOrder,
  PortalOrderCreate
} from '../../services/client-portal.service';

@Component({
  selector: 'app-client-portal',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDividerModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTabsModule
  ],
  templateUrl: './client-portal.component.html',
  styleUrl: './client-portal.component.css'
})
export class ClientPortalComponent implements OnInit {
  customer: PortalCustomer | null = null;
  orders: PortalOrder[] = [];
  loading = false;
  ordersLoading = false;
  decisionLoading = false;
  error = '';
  success = '';
  authMode: 'login' | 'register' = 'login';
  hidePassword = true;

  loginForm!: FormGroup;
  registerForm!: FormGroup;
  orderForm!: FormGroup;
  trackForm!: FormGroup;
  trackedOrder: PortalOrder | null = null;

  constructor(
    private fb: FormBuilder,
    private portalService: ClientPortalService
  ) {
    this.loginForm = this.fb.group({
      phone: ['', [Validators.required, Validators.minLength(10)]],
      password: ['', [Validators.required, Validators.minLength(8)]]
    });

    this.registerForm = this.fb.group({
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      phone: ['', [Validators.required, Validators.minLength(10)]],
      email: [''],
      password: ['', [Validators.required, Validators.minLength(8)]]
    });

    this.orderForm = this.fb.group({
      device_type: ['Телефон', Validators.required],
      brand: ['', Validators.required],
      model_name: ['', Validators.required],
      serial_number: [''],
      imei: [''],
      color: [''],
      storage_capacity: [''],
      accessories: [''],
      device_condition: [''],
      problem_description: ['', [Validators.required, Validators.minLength(10)]],
      cost_estimate: [0, [Validators.required, Validators.min(0)]]
    });

    this.trackForm = this.fb.group({
      order_number: ['', Validators.required],
      phone: ['', [Validators.required, Validators.minLength(10)]]
    });
  }

  ngOnInit(): void {
    this.portalService.customer$.subscribe(customer => {
      this.customer = customer;
      if (customer) {
        this.loadOrders();
      }
    });

    if (this.portalService.isAuthenticated()) {
      this.portalService.me().subscribe({
        error: () => this.portalService.logout()
      });
    }
  }

  switchAuthMode(mode: 'login' | 'register'): void {
    this.authMode = mode;
    this.clearMessages();
  }

  login(): void {
    if (this.loginForm.invalid) {
      return;
    }
    this.loading = true;
    this.clearMessages();
    this.portalService.login(this.loginForm.getRawValue() as { phone: string; password: string })
      .pipe(finalize(() => this.loading = false))
      .subscribe({
        next: () => this.success = 'Вы вошли в кабинет',
        error: error => this.error = this.extractError(error)
      });
  }

  register(): void {
    if (this.registerForm.invalid) {
      return;
    }
    this.loading = true;
    this.clearMessages();
    this.portalService.register({
      ...this.registerForm.getRawValue(),
      marketing_consent: true
    }).pipe(finalize(() => this.loading = false))
      .subscribe({
        next: () => this.success = 'Кабинет создан',
        error: error => this.error = this.extractError(error)
      });
  }

  submitOrder(): void {
    if (this.orderForm.invalid) {
      return;
    }
    this.loading = true;
    this.clearMessages();
    this.portalService.createOrder(this.orderForm.getRawValue() as PortalOrderCreate)
      .pipe(finalize(() => this.loading = false))
      .subscribe({
        next: order => {
          this.success = `Заявка ${order.order_number} принята`;
          this.orderForm.patchValue({
            brand: '',
            model_name: '',
            serial_number: '',
            imei: '',
            color: '',
            storage_capacity: '',
            accessories: '',
            device_condition: '',
            problem_description: '',
            cost_estimate: 0
          });
          this.loadOrders();
        },
        error: error => this.error = this.extractError(error)
      });
  }

  trackOrder(): void {
    if (this.trackForm.invalid) {
      return;
    }
    this.loading = true;
    this.trackedOrder = null;
    this.clearMessages();
    this.portalService.trackOrder(this.trackForm.getRawValue())
      .pipe(finalize(() => this.loading = false))
      .subscribe({
        next: order => this.trackedOrder = order,
        error: error => this.error = this.extractError(error)
      });
  }

  approveApproval(approvalId: number): void {
    this.decideApproval(approvalId, true);
  }

  rejectApproval(approvalId: number): void {
    this.decideApproval(approvalId, false);
  }

  logout(): void {
    this.portalService.logout();
    this.orders = [];
    this.clearMessages();
  }

  trackByOrderId(index: number, order: PortalOrder): number {
    return order.id;
  }

  statusClass(order: PortalOrder): string {
    return `status-${order.status}`;
  }

  hasPendingApprovals(order: PortalOrder): boolean {
    return order.approvals.some(approval => approval.status === 'pending');
  }

  private loadOrders(): void {
    this.ordersLoading = true;
    this.portalService.orders()
      .pipe(finalize(() => this.ordersLoading = false))
      .subscribe({
        next: orders => this.orders = orders,
        error: error => this.error = this.extractError(error)
      });
  }

  private clearMessages(): void {
    this.error = '';
    this.success = '';
  }

  private decideApproval(approvalId: number, approve: boolean): void {
    if (this.decisionLoading) {
      return;
    }
    this.decisionLoading = true;
    this.clearMessages();
    const request = approve
      ? this.portalService.approveApproval(approvalId)
      : this.portalService.rejectApproval(approvalId);

    request.pipe(finalize(() => this.decisionLoading = false))
      .subscribe({
        next: () => {
          this.success = approve ? 'Согласование принято' : 'Согласование отклонено';
          this.loadOrders();
        },
        error: error => this.error = this.extractError(error)
      });
  }

  private extractError(error: { error?: { error?: string } }): string {
    return error.error?.error || 'Не удалось выполнить действие';
  }
}

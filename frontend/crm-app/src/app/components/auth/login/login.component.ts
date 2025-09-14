import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { AppState } from '../../../store/app.state';
import { selectAuthLoading, selectAuthError } from '../../../store/auth/auth.selectors';
import * as AuthActions from '../../../store/auth/auth.actions';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatIconModule
  ],
  template: `
    <div class="login-container">
      <mat-card class="login-card">
        <mat-card-header>
          <mat-card-title class="text-center">
            <mat-icon class="login-icon">build</mat-icon>
            <h1>Repair CRM</h1>
          </mat-card-title>
          <mat-card-subtitle class="text-center">
            Система управления ремонтом устройств
          </mat-card-subtitle>
        </mat-card-header>

        <mat-card-content>
          <form [formGroup]="loginForm" (ngSubmit)="onSubmit()">
            <mat-form-field class="full-width">
              <mat-label>Логин</mat-label>
              <input matInput formControlName="username" required>
              <mat-icon matSuffix>person</mat-icon>
              <mat-error *ngIf="loginForm.get('username')?.hasError('required')">
                Логин обязателен
              </mat-error>
            </mat-form-field>

            <mat-form-field class="full-width">
              <mat-label>Пароль</mat-label>
              <input matInput 
                     [type]="hidePassword ? 'password' : 'text'" 
                     formControlName="password" 
                     required>
              <button mat-icon-button 
                      matSuffix 
                      (click)="hidePassword = !hidePassword"
                      type="button">
                <mat-icon>{{hidePassword ? 'visibility_off' : 'visibility'}}</mat-icon>
              </button>
              <mat-error *ngIf="loginForm.get('password')?.hasError('required')">
                Пароль обязателен
              </mat-error>
            </mat-form-field>

            <div *ngIf="error$ | async as error" class="error-message">
              <mat-icon>error</mat-icon>
              {{ error }}
            </div>

            <button mat-raised-button 
                    color="primary" 
                    type="submit" 
                    class="full-width login-button"
                    [disabled]="loginForm.invalid || (loading$ | async)">
              <mat-spinner *ngIf="loading$ | async" diameter="20"></mat-spinner>
              <span *ngIf="!(loading$ | async)">Войти</span>
            </button>
          </form>

          <div class="demo-credentials">
            <h4>Тестовые данные:</h4>
            <p><strong>Директор:</strong> director / director123</p>
            <p><strong>Менеджер:</strong> manager / manager123</p>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .login-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 20px;
    }

    .login-card {
      width: 100%;
      max-width: 400px;
      padding: 20px;
    }

    .login-icon {
      font-size: 48px;
      height: 48px;
      width: 48px;
      color: #1976d2;
    }

    .login-button {
      margin-top: 20px;
      height: 48px;
    }

    .error-message {
      color: #f44336;
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 16px 0;
      padding: 12px;
      background: #ffebee;
      border-radius: 4px;
    }

    .demo-credentials {
      margin-top: 24px;
      padding: 16px;
      background: #f5f5f5;
      border-radius: 4px;
      text-align: center;
    }

    .demo-credentials h4 {
      margin: 0 0 12px 0;
      color: #666;
    }

    .demo-credentials p {
      margin: 4px 0;
      font-size: 14px;
      color: #888;
    }
  `]
})
export class LoginComponent implements OnInit {
  loginForm: FormGroup;
  hidePassword = true;
  loading$: Observable<boolean>;
  error$: Observable<string | null>;

  constructor(
    private fb: FormBuilder,
    private store: Store<AppState>
  ) {
    this.loginForm = this.fb.group({
      username: ['', Validators.required],
      password: ['', Validators.required]
    });

    this.loading$ = this.store.select(selectAuthLoading);
    this.error$ = this.store.select(selectAuthError);
  }

  ngOnInit(): void {
    // Очищаем ошибки при инициализации
    this.loginForm.valueChanges.subscribe(() => {
      // Можно добавить логику для очистки ошибок при изменении формы
    });
  }

  onSubmit(): void {
    if (this.loginForm.valid) {
      this.store.dispatch(AuthActions.login({
        credentials: this.loginForm.value
      }));
    }
  }
}
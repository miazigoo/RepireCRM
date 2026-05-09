import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { finalize } from 'rxjs';
import { PromoCode, Promotion, Shop } from '../../../core/models/models';
import { AuthService } from '../../../services/auth.service';
import { PromotionsService } from '../../../services/promotions.service';

@Component({
  selector: 'app-promotions-management',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatChipsModule,
    MatDividerModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  templateUrl: './promotions-management.component.html',
  styleUrl: './promotions-management.component.scss',
})
export class PromotionsManagementComponent implements OnInit {
  promotions: Promotion[] = [];
  promoCodes: PromoCode[] = [];
  shops: Shop[] = [];
  promotionForm: FormGroup;
  promoCodeForm: FormGroup;
  quoteForm: FormGroup;
  editingPromotion: Promotion | null = null;
  editingPromoCode: PromoCode | null = null;
  loading = false;
  savingPromotion = false;
  savingCode = false;
  validating = false;
  quoteMessage = '';

  readonly discountTypes = [
    { value: 'percent', label: 'Процент' },
    { value: 'fixed', label: 'Сумма' },
  ];

  private moneyFormatter = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0,
  });

  constructor(
    private fb: FormBuilder,
    private promotionsService: PromotionsService,
    private authService: AuthService,
    private snackBar: MatSnackBar,
  ) {
    this.promotionForm = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(160)]],
      description: [''],
      discount_type: ['percent', Validators.required],
      value: [10, [Validators.required, Validators.min(0)]],
      max_discount_amount: [null],
      min_order_amount: [0, [Validators.required, Validators.min(0)]],
      starts_at: [''],
      ends_at: [''],
      is_active: [true],
      auto_apply: [false],
      stackable: [false],
      usage_limit: [null],
      per_customer_limit: [null],
      shop_ids: [[]],
    });
    this.promoCodeForm = this.fb.group({
      promotion_id: [null, Validators.required],
      code: ['', [Validators.required, Validators.maxLength(40)]],
      description: [''],
      is_active: [true],
      starts_at: [''],
      ends_at: [''],
      usage_limit: [null],
      per_customer_limit: [null],
    });
    this.quoteForm = this.fb.group({
      code: ['', Validators.required],
      subtotal: [5000, [Validators.required, Validators.min(0)]],
    });
  }

  ngOnInit(): void {
    this.loadAll();
    this.authService.getAvailableShops().subscribe({
      next: (shops) => (this.shops = shops.filter((shop) => shop.is_active)),
      error: () => (this.shops = []),
    });
  }

  loadAll(): void {
    this.loading = true;
    this.promotionsService
      .getPromotions(true)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (promotions) => {
          this.promotions = promotions;
          this.loadCodes();
        },
        error: (error) => this.showError(error, 'Не удалось загрузить акции'),
      });
  }

  loadCodes(): void {
    this.promotionsService.getPromoCodes(true).subscribe({
      next: (codes) => (this.promoCodes = codes),
      error: (error) => this.showError(error, 'Не удалось загрузить промокоды'),
    });
  }

  savePromotion(): void {
    if (this.promotionForm.invalid || this.savingPromotion) {
      this.promotionForm.markAllAsTouched();
      return;
    }

    const payload = this.normalizePayload(this.promotionForm.getRawValue());
    const request$ = this.editingPromotion
      ? this.promotionsService.updatePromotion(this.editingPromotion.id, payload)
      : this.promotionsService.createPromotion(payload);

    this.savingPromotion = true;
    request$.pipe(finalize(() => (this.savingPromotion = false))).subscribe({
      next: () => {
        this.resetPromotionForm();
        this.loadAll();
        this.snackBar.open('Акция сохранена', 'Закрыть', { duration: 2500 });
      },
      error: (error) => this.showError(error, 'Не удалось сохранить акцию'),
    });
  }

  savePromoCode(): void {
    if (this.promoCodeForm.invalid || this.savingCode) {
      this.promoCodeForm.markAllAsTouched();
      return;
    }

    const payload = this.normalizePayload(this.promoCodeForm.getRawValue());
    payload['code'] = String(payload['code'] || '').trim().toUpperCase();
    const request$ = this.editingPromoCode
      ? this.promotionsService.updatePromoCode(this.editingPromoCode.id, payload)
      : this.promotionsService.createPromoCode(payload);

    this.savingCode = true;
    request$.pipe(finalize(() => (this.savingCode = false))).subscribe({
      next: () => {
        this.resetPromoCodeForm();
        this.loadCodes();
        this.snackBar.open('Промокод сохранен', 'Закрыть', { duration: 2500 });
      },
      error: (error) => this.showError(error, 'Не удалось сохранить промокод'),
    });
  }

  editPromotion(promotion: Promotion): void {
    this.editingPromotion = promotion;
    this.promotionForm.patchValue({
      ...promotion,
      starts_at: this.toDatetimeLocal(promotion.starts_at),
      ends_at: this.toDatetimeLocal(promotion.ends_at),
      max_discount_amount: promotion.max_discount_amount ?? null,
      usage_limit: promotion.usage_limit ?? null,
      per_customer_limit: promotion.per_customer_limit ?? null,
    });
  }

  editPromoCode(code: PromoCode): void {
    this.editingPromoCode = code;
    this.promoCodeForm.patchValue({
      ...code,
      starts_at: this.toDatetimeLocal(code.starts_at),
      ends_at: this.toDatetimeLocal(code.ends_at),
      usage_limit: code.usage_limit ?? null,
      per_customer_limit: code.per_customer_limit ?? null,
    });
  }

  disablePromotion(promotion: Promotion): void {
    this.promotionsService.disablePromotion(promotion.id).subscribe({
      next: () => {
        this.loadAll();
        this.snackBar.open('Акция отключена', 'Закрыть', { duration: 2500 });
      },
      error: (error) => this.showError(error, 'Не удалось отключить акцию'),
    });
  }

  disablePromoCode(code: PromoCode): void {
    this.promotionsService.disablePromoCode(code.id).subscribe({
      next: () => {
        this.loadCodes();
        this.snackBar.open('Промокод отключен', 'Закрыть', { duration: 2500 });
      },
      error: (error) => this.showError(error, 'Не удалось отключить промокод'),
    });
  }

  validatePromoCode(): void {
    if (this.quoteForm.invalid || this.validating) {
      this.quoteForm.markAllAsTouched();
      return;
    }

    this.validating = true;
    this.promotionsService
      .validatePromoCode(this.quoteForm.getRawValue())
      .pipe(finalize(() => (this.validating = false)))
      .subscribe({
        next: (quote) => {
          this.quoteMessage = quote.valid
            ? `${quote.promotion_name}: скидка ${this.formatMoney(quote.discount_amount)}, итог ${this.formatMoney(quote.total_after_discount)}`
            : quote.message;
        },
        error: (error) => this.showError(error, 'Не удалось проверить промокод'),
      });
  }

  resetPromotionForm(): void {
    this.editingPromotion = null;
    this.promotionForm.reset({
      name: '',
      description: '',
      discount_type: 'percent',
      value: 10,
      max_discount_amount: null,
      min_order_amount: 0,
      starts_at: '',
      ends_at: '',
      is_active: true,
      auto_apply: false,
      stackable: false,
      usage_limit: null,
      per_customer_limit: null,
      shop_ids: [],
    });
  }

  resetPromoCodeForm(): void {
    this.editingPromoCode = null;
    this.promoCodeForm.reset({
      promotion_id: null,
      code: '',
      description: '',
      is_active: true,
      starts_at: '',
      ends_at: '',
      usage_limit: null,
      per_customer_limit: null,
    });
  }

  getPromotionName(id: number): string {
    return this.promotions.find((promotion) => promotion.id === id)?.name || 'Акция';
  }

  getDiscountLabel(promotion: Promotion): string {
    if (promotion.discount_type === 'percent') {
      return `${promotion.value}%`;
    }
    return this.formatMoney(promotion.value);
  }

  getScopeLabel(shopIds: number[]): string {
    if (!shopIds?.length) {
      return 'Все филиалы';
    }
    const names = this.shops.filter((shop) => shopIds.includes(shop.id)).map((shop) => shop.name);
    return names.length ? names.join(', ') : 'Выбранные филиалы';
  }

  formatMoney(value: number): string {
    return `${this.moneyFormatter.format(Number(value || 0))} ₽`;
  }

  trackById(_: number, item: { id: number }): number {
    return item.id;
  }

  private normalizePayload(payload: Record<string, any>): Record<string, any> {
    return Object.fromEntries(
      Object.entries(payload).map(([key, value]) => {
        if (value === '') {
          return [key, null];
        }
        return [key, value];
      }),
    );
  }

  private toDatetimeLocal(value?: string | null): string {
    if (!value) {
      return '';
    }
    const date = new Date(value);
    date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
    return date.toISOString().slice(0, 16);
  }

  private showError(error: any, fallback: string): void {
    this.snackBar.open(error?.error?.error || error?.error?.detail || fallback, 'Закрыть', {
      duration: 4200,
    });
  }
}

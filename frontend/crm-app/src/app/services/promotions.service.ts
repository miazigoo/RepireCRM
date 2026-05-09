import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  DiscountQuote,
  OrderDiscount,
  PromoCode,
  Promotion,
} from '../core/models/models';
import { ApiService } from './api.service';

export type PromotionPayload = Partial<Omit<Promotion, 'id' | 'created_at' | 'updated_at' | 'used_count'>>;
export type PromoCodePayload = Partial<Omit<PromoCode, 'id' | 'created_at' | 'updated_at' | 'used_count' | 'promotion_name'>>;

@Injectable({
  providedIn: 'root',
})
export class PromotionsService {
  constructor(private apiService: ApiService) {}

  getPromotions(includeInactive = false): Observable<Promotion[]> {
    const params = includeInactive ? { include_inactive: true } : undefined;
    return this.apiService.get<Promotion[]>('/promotions/campaigns', params);
  }

  createPromotion(payload: PromotionPayload): Observable<Promotion> {
    return this.apiService.post<Promotion>('/promotions/campaigns', payload);
  }

  updatePromotion(id: number, payload: PromotionPayload): Observable<Promotion> {
    return this.apiService.put<Promotion>(`/promotions/campaigns/${id}`, payload);
  }

  disablePromotion(id: number): Observable<{ success: boolean }> {
    return this.apiService.delete<{ success: boolean }>(`/promotions/campaigns/${id}`);
  }

  getPromoCodes(includeInactive = false): Observable<PromoCode[]> {
    const params = includeInactive ? { include_inactive: true } : undefined;
    return this.apiService.get<PromoCode[]>('/promotions/codes', params);
  }

  createPromoCode(payload: PromoCodePayload): Observable<PromoCode> {
    return this.apiService.post<PromoCode>('/promotions/codes', payload);
  }

  updatePromoCode(id: number, payload: PromoCodePayload): Observable<PromoCode> {
    return this.apiService.put<PromoCode>(`/promotions/codes/${id}`, payload);
  }

  disablePromoCode(id: number): Observable<{ success: boolean }> {
    return this.apiService.delete<{ success: boolean }>(`/promotions/codes/${id}`);
  }

  validatePromoCode(payload: {
    code: string;
    order_id?: number;
    customer_id?: number;
    subtotal?: number;
  }): Observable<DiscountQuote> {
    return this.apiService.post<DiscountQuote>('/promotions/validate-code', payload);
  }

  applyPromoCode(orderId: number, code: string): Observable<OrderDiscount> {
    return this.apiService.post<OrderDiscount>(`/promotions/orders/${orderId}/apply-code`, { code });
  }

  addManualDiscount(orderId: number, payload: { label: string; amount: number }): Observable<OrderDiscount> {
    return this.apiService.post<OrderDiscount>(`/promotions/orders/${orderId}/manual-discount`, payload);
  }

  deleteOrderDiscount(orderId: number, discountId: number): Observable<{ success: boolean }> {
    return this.apiService.delete<{ success: boolean }>(`/promotions/orders/${orderId}/discounts/${discountId}`);
  }
}

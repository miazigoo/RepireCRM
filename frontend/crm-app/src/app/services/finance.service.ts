import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ApiService } from './api.service';

export interface FinancialSummary {
  total_income: number;
  total_expenses: number;
  net_profit: number;
  cash_balance: number;
  pending_payments: number;
  profit_margin: number;
}

export interface RecentTransaction {
  id: number;
  type: 'income' | 'expense';
  amount: number;
  description: string;
  date: string;
  status: 'completed' | 'pending' | 'cancelled';
  payment_method: string;
}

export interface ProfitChart {
  labels: string[];
  income: number[];
  expenses: number[];
  profit: number[];
}

export interface ExpensesBreakdown {
  categories: string[];
  amounts: number[];
}

@Injectable({
  providedIn: 'root'
})
export class FinanceService {
  constructor(private apiService: ApiService) {}

  getFinancialSummary(filters: Record<string, unknown>): Observable<FinancialSummary> {
    return this.apiService.get<FinancialSummary>('/finance/summary', filters).pipe(
      catchError(() => of({
        total_income: 0,
        total_expenses: 0,
        net_profit: 0,
        cash_balance: 0,
        pending_payments: 0,
        profit_margin: 0
      }))
    );
  }

  getRecentTransactions(): Observable<RecentTransaction[]> {
    return this.apiService.get<RecentTransaction[]>('/finance/transactions/recent').pipe(
      catchError(() => of([]))
    );
  }

  getProfitChart(filters: Record<string, unknown>): Observable<ProfitChart> {
    return this.apiService.get<ProfitChart>('/finance/charts/profit', filters).pipe(
      catchError(() => of({ labels: [], income: [], expenses: [], profit: [] }))
    );
  }

  getExpensesBreakdown(filters: Record<string, unknown>): Observable<ExpensesBreakdown> {
    return this.apiService.get<ExpensesBreakdown>('/finance/charts/expenses', filters).pipe(
      catchError(() => of({ categories: [], amounts: [] }))
    );
  }

  exportFinancialReport(filters: Record<string, unknown>): Observable<Blob> {
    return this.apiService.getBlob('/finance/export', filters);
  }
}

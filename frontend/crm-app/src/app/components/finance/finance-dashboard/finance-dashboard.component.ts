import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData } from 'chart.js';
import { FinanceService } from '../../../services/finance.service';

interface FinancialSummary {
  total_income: number;
  total_expenses: number;
  net_profit: number;
  cash_balance: number;
  pending_payments: number;
  profit_margin: number;
}

interface RecentTransaction {
  id: number;
  type: 'income' | 'expense';
  amount: number;
  description: string;
  date: string;
  status: 'completed' | 'pending' | 'cancelled';
  payment_method: string;
}

@Component({
  selector: 'app-finance-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatTableModule,
    MatChipsModule,
    MatMenuModule,
    MatDatepickerModule,
    MatFormFieldModule,
    MatSelectModule,
    BaseChartDirective
  ],
  templateUrl: './finance-dashboard.component.html',
  styleUrl: './finance-dashboard.component.css'
})
export class FinanceDashboardComponent implements OnInit {
  filtersForm: FormGroup;
  loading = false;

  summary: FinancialSummary = {
    total_income: 0,
    total_expenses: 0,
    net_profit: 0,
    cash_balance: 0,
    pending_payments: 0,
    profit_margin: 0
  };

  recentTransactions: RecentTransaction[] = [];

  // Графики
  profitChartData: ChartData<'line'> | null = null;
  expensesChartData: ChartData<'doughnut'> | null = null;
  cashFlowChartData: ChartData<'bar'> | null = null;

  profitChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Динамика прибыли'
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: function(value) {
            return new Intl.NumberFormat('ru-RU', {
              style: 'currency',
              currency: 'RUB',
              maximumFractionDigits: 0
            }).format(Number(value));
          }
        }
      }
    }
  };

  expensesChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Структура расходов'
      },
      legend: {
        position: 'right'
      }
    }
  };

  transactionColumns = ['type', 'description', 'amount', 'payment_method', 'date', 'status', 'actions'];
  transactionDataSource = new MatTableDataSource<RecentTransaction>();

  constructor(
    private fb: FormBuilder,
    private financeService: FinanceService
  ) {
    this.filtersForm = this.fb.group({
      period: ['30_days'],
      date_from: [null],
      date_to: [null]
    });
  }

  ngOnInit(): void {
    this.loadFinancialData();
    this.setupFilters();
  }

  private setupFilters(): void {
    this.filtersForm.valueChanges.subscribe(() => {
      this.loadFinancialData();
    });
  }

  private loadFinancialData(): void {
    this.loading = true;

    // Загружаем основные данные
    Promise.all([
      this.financeService.getFinancialSummary(this.filtersForm.value).toPromise(),
      this.financeService.getRecentTransactions().toPromise(),
      this.financeService.getProfitChart(this.filtersForm.value).toPromise(),
      this.financeService.getExpensesBreakdown(this.filtersForm.value).toPromise()
    ]).then(([summary, transactions, profitData, expensesData]) => {
      this.summary = summary;
      this.recentTransactions = transactions;
      this.transactionDataSource.data = transactions;

      this.setupCharts(profitData, expensesData);
      this.loading = false;
    }).catch(error => {
      console.error('Error loading financial data:', error);
      this.loading = false;
    });
  }

  private setupCharts(profitData: any, expensesData: any): void {
    // График прибыли
    this.profitChartData = {
      labels: profitData.labels,
      datasets: [
        {
          label: 'Доходы',
          data: profitData.income,
          borderColor: '#4caf50',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          fill: true
        },
        {
          label: 'Расходы',
          data: profitData.expenses,
          borderColor: '#f44336',
          backgroundColor: 'rgba(244, 67, 54, 0.1)',
          fill: true
        },
        {
          label: 'Прибыль',
          data: profitData.profit,
          borderColor: '#2196f3',
          backgroundColor: 'rgba(33, 150, 243, 0.1)',
          fill: true
        }
      ]
    };

    // График расходов
    this.expensesChartData = {
      labels: expensesData.categories,
      datasets: [{
        data: expensesData.amounts,
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF',
          '#FF9F40',
          '#FF6384',
          '#C9CBCF'
        ]
      }]
    };
  }

  getTransactionTypeIcon(type: string): string {
    return type === 'income' ? 'arrow_downward' : 'arrow_upward';
  }

  getTransactionTypeClass(type: string): string {
    return type === 'income' ? 'transaction-income' : 'transaction-expense';
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'completed': return 'status-completed';
      case 'pending': return 'status-pending';
      case 'cancelled': return 'status-cancelled';
      default: return '';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'completed': return 'Выполнено';
      case 'pending': return 'Ожидает';
      case 'cancelled': return 'Отменено';
      default: return status;
    }
  }

  formatCurrency(value: number): string {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0
    }).format(value);
  }

  formatPercent(value: number): string {
    return `${value.toFixed(1)}%`;
  }

  exportFinancialReport(): void {
    this.financeService.exportFinancialReport(this.filtersForm.value).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'financial-report.pdf';
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (error) => {
        console.error('Error exporting report:', error);
      }
    });
  }

  createExpense(): void {
    // Переход к созданию расхода
  }

  viewTransaction(transaction: RecentTransaction): void {
    // Просмотр деталей транзакции
  }
}

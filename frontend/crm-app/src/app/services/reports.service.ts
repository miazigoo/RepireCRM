// frontend/src/app/services/reports.service.ts
@Injectable({
  providedIn: 'root'
})
export class ReportsService {
  constructor(private apiService: ApiService) {}

  getDashboardMetrics(): Observable<DashboardMetrics> {
    return this.apiService.get<DashboardMetrics>('/reports/dashboard');
  }

  getFinancialReport(dateFrom: string, dateTo: string): Observable<FinancialReport> {
    return this.apiService.get<FinancialReport>('/reports/financial', {
      date_from: dateFrom,
      date_to: dateTo
    });
  }

  exportReport(reportType: string, format: 'pdf' | 'excel', params: any): Observable<Blob> {
    return this.apiService.get<Blob>(`/reports/export/${reportType}`,
      { ...params, format },
      { responseType: 'blob' }
    );
  }
}

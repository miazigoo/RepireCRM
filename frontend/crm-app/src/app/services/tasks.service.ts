import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ApiService } from './api.service';

export interface Task {
  id: number;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'overdue';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  assignment_type: 'individual' | 'shop' | 'all_shops' | 'role';
  assigned_to?: string;
  assigned_shop?: string;
  due_date?: string;
  created_by: string;
  created_at: string;
  progress_percent: number;
  category?: string;
}

export interface TasksSummary {
  total_tasks: number;
  status_breakdown: Record<string, number>;
  overdue_tasks: number;
  due_today: number;
  priority_breakdown: Record<string, number>;
}

@Injectable({
  providedIn: 'root'
})
export class TasksService {
  constructor(private apiService: ApiService) {}

  getMyTasksSummary(): Observable<TasksSummary> {
    return this.apiService.get<TasksSummary>('/tasks/summary').pipe(
      catchError(() => of({
        total_tasks: 0,
        status_breakdown: {},
        overdue_tasks: 0,
        due_today: 0,
        priority_breakdown: {}
      }))
    );
  }

  getTasks(filters: Record<string, unknown>): Observable<Task[]> {
    return this.apiService.get<Task[]>('/tasks', filters).pipe(
      catchError(() => of([]))
    );
  }

  updateTask(taskId: number, data: Partial<Task>): Observable<Task> {
    return this.apiService.put<Task>(`/tasks/${taskId}`, data);
  }
}

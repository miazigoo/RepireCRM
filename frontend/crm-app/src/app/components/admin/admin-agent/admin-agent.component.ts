import { DatePipe, NgClass, NgFor, NgIf } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { catchError, finalize, forkJoin, of } from 'rxjs';

import {
  AdminAgentStatus,
  AdminService,
  AdminSupportMessage,
  AdminSupportThread,
} from '../../../services/admin.service';

@Component({
  selector: 'app-admin-agent',
  standalone: true,
  imports: [
    NgIf,
    NgFor,
    NgClass,
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: './admin-agent.component.html',
  styleUrl: './admin-agent.component.scss',
})
export class AdminAgentComponent implements OnInit {
  status: AdminAgentStatus | null = null;
  threads: AdminSupportThread[] = [];
  selectedThread: AdminSupportThread | null = null;
  messages: AdminSupportMessage[] = [];
  loading = false;
  heartbeatLoading = false;
  messagesLoading = false;
  threadForm!: FormGroup;
  replyForm!: FormGroup;

  constructor(
    private adminService: AdminService,
    private fb: FormBuilder,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.threadForm = this.fb.group({
      subject: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(255)]],
      priority: ['normal', Validators.required],
      body: ['', [Validators.required, Validators.maxLength(10000)]],
    });
    this.replyForm = this.fb.group({
      body: ['', [Validators.required, Validators.maxLength(10000)]],
    });
    this.showDeferredSubscriptionMessage();
    this.load();
  }

  load(): void {
    this.loading = true;
    forkJoin({
      status: this.adminService.getAdminAgentStatus(),
      threads: this.adminService
        .getAdminSupportThreads()
        .pipe(catchError(() => of([] as AdminSupportThread[]))),
    })
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: ({ status, threads }) => {
          this.status = status;
          this.threads = threads;
          if (this.selectedThread) {
            this.selectedThread =
              threads.find((thread) => thread.id === this.selectedThread?.id) || null;
          }
        },
        error: () => {
          this.snackBar.open('Не удалось загрузить связь с центральной админкой', 'Закрыть', {
            duration: 3500,
          });
        },
      });
  }

  sendHeartbeat(): void {
    this.heartbeatLoading = true;
    this.adminService
      .sendAdminAgentHeartbeat()
      .pipe(finalize(() => (this.heartbeatLoading = false)))
      .subscribe({
        next: () => {
          this.snackBar.open('Heartbeat отправлен', 'Закрыть', { duration: 2500 });
          this.load();
        },
        error: () => {
          this.snackBar.open('Heartbeat не прошел', 'Закрыть', { duration: 3500 });
          this.load();
        },
      });
  }

  createThread(): void {
    if (this.threadForm.invalid) {
      this.threadForm.markAllAsTouched();
      return;
    }

    this.adminService.createAdminSupportThread(this.threadForm.getRawValue()).subscribe({
      next: (thread) => {
        this.threadForm.reset({ priority: 'normal' });
        this.threads = [thread, ...this.threads];
        this.openThread(thread);
      },
      error: () => {
        this.snackBar.open('Не удалось создать обращение', 'Закрыть', { duration: 3500 });
      },
    });
  }

  openThread(thread: AdminSupportThread): void {
    this.selectedThread = thread;
    this.messagesLoading = true;
    this.adminService
      .getAdminSupportMessages(thread.id)
      .pipe(finalize(() => (this.messagesLoading = false)))
      .subscribe({
        next: (messages) => {
          this.messages = messages;
          this.load();
        },
        error: () => {
          this.snackBar.open('Не удалось загрузить переписку', 'Закрыть', { duration: 3500 });
        },
      });
  }

  sendReply(): void {
    if (!this.selectedThread || this.replyForm.invalid) {
      this.replyForm.markAllAsTouched();
      return;
    }

    this.adminService
      .replyAdminSupportThread(this.selectedThread.id, this.replyForm.getRawValue())
      .subscribe({
        next: (message) => {
          this.messages = [...this.messages, message];
          this.replyForm.reset();
          this.load();
        },
        error: () => {
          this.snackBar.open('Не удалось отправить сообщение', 'Закрыть', { duration: 3500 });
        },
      });
  }

  statusClass(value?: string | null): string {
    if (!value) {
      return 'muted';
    }
    if (['active', 'ok', 'trial', 'paid'].includes(value)) {
      return 'ok';
    }
    if (['expired', 'suspended', 'down', 'cancelled'].includes(value)) {
      return 'danger';
    }
    return 'warn';
  }

  threadTone(thread: AdminSupportThread): string {
    if (thread.status === 'closed') {
      return 'muted';
    }
    if (thread.priority === 'urgent' || thread.priority === 'high') {
      return 'danger';
    }
    if (thread.unread_client > 0) {
      return 'ok';
    }
    return 'warn';
  }

  trackByThread(_: number, thread: AdminSupportThread): number {
    return thread.id;
  }

  trackByMessage(_: number, message: AdminSupportMessage): number {
    return message.id;
  }

  private showDeferredSubscriptionMessage(): void {
    const message = sessionStorage.getItem('repaircrm.subscriptionBlockMessage');
    if (!message) {
      return;
    }
    sessionStorage.removeItem('repaircrm.subscriptionBlockMessage');
    this.snackBar.open(message, 'Закрыть', { duration: 7000 });
  }
}

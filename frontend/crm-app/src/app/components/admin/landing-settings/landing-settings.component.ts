import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import {
  FormArray,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { BehaviorSubject, catchError, finalize, forkJoin, of } from 'rxjs';
import { map, startWith } from 'rxjs/operators';

import {
  AdminService,
  ClientPortalIntegration,
  ClientLandingConfig,
  ClientLandingPromoSpotlight,
  ClientLandingCard,
} from '../../../services/admin.service';

type CardIconValue = 'status' | 'pricing' | 'map' | 'visit' | 'shield' | 'sparkle';

interface CardIconOption {
  value: CardIconValue;
  label: string;
  path: string;
}

const CARD_ICONS: CardIconOption[] = [
  {
    value: 'status',
    label: 'Статус ремонта',
    path: 'M5 6.5h14v11H5zM8 10h5M8 14h8M15.5 9l1.5 1.5L20 8',
  },
  {
    value: 'pricing',
    label: 'Смета и цена',
    path: 'M7 5h10l3 3v11H7zM14 5v4h6M10 12h6M10 16h4M16 15.5h2.5',
  },
  {
    value: 'map',
    label: 'Карта точек',
    path: 'M5 6l5-2 4 2 5-2v14l-5 2-4-2-5 2zM10 4v14M14 6v14',
  },
  {
    value: 'visit',
    label: 'Выезд мастера',
    path: 'M5 15h2.5M16.5 15H19v-3l-2-3h-3V6H5v9M8 17.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5M16 17.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5M14 9h3',
  },
  {
    value: 'shield',
    label: 'Гарантия',
    path: 'M12 4l7 3v5c0 4.6-2.9 7.7-7 9-4.1-1.3-7-4.4-7-9V7zM8.8 12.2l2.1 2.1 4.6-4.8',
  },
  {
    value: 'sparkle',
    label: 'Акцент',
    path: 'M12 4l1.8 4.2L18 10l-4.2 1.8L12 16l-1.8-4.2L6 10l4.2-1.8zM18 14l.9 2.1L21 17l-2.1.9L18 20l-.9-2.1L15 17l2.1-.9z',
  },
];

const DEFAULT_FEATURE_CARDS: ClientLandingCard[] = [
  {
    title: 'Статус ремонта',
    body: 'Диагностика, запчасти, ремонт и готовность — в одной ленте, без догадок.',
    icon: 'status',
  },
  {
    title: 'Смета до оплаты',
    body: 'Согласуйте допработы в пару кликов — суммы и детали всегда перед глазами.',
    icon: 'pricing',
  },
  {
    title: 'Сервисы на карте',
    body: 'Точки приёма и маршрут во внешних картах — вы выбираете, как добраться.',
    icon: 'map',
  },
];

@Component({
  selector: 'app-landing-settings',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatDividerModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  templateUrl: './landing-settings.component.html',
  styleUrls: ['./landing-settings.component.scss'],
})
export class LandingSettingsComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly admin = inject(AdminService);
  private readonly snack = inject(MatSnackBar);

  readonly cardIcons = CARD_ICONS;

  loading = false;
  saving = false;
  loadError = '';
  integration: ClientPortalIntegration | null = null;
  lastSavedAt: Date | null = null;

  form!: FormGroup;

  private previewSubject = new BehaviorSubject<ClientLandingConfig | null>(null);
  readonly previewVm$ = this.previewSubject.asObservable();

  ngOnInit(): void {
    this.form = this.fb.group({
      landing_section_eyebrow: [''],
      landing_section_title: [''],
      landing_section_subtitle: [''],
      cards: this.fb.array<FormGroup>([]),
      promo: this.fb.group({
        enabled: [false],
        title: [''],
        subtitle: [''],
        body: [''],
        badge: [''],
        cta_label: [''],
        cta_href: ['/login?register=1'],
        image_url: [''],
      }),
    });

    for (let i = 0; i < 4; i++) {
      this.cards.push(
        this.fb.group({
          title: ['', Validators.maxLength(200)],
          body: ['', Validators.maxLength(1200)],
          icon: ['status'],
        }),
      );
    }

    this.form.valueChanges
      .pipe(
        /*
         * Предпросмотр будет успевать только после первого patch после загрузки -
         * startWith ниже + явное обновление в load().
         */
        startWith(this.form.getRawValue()),
        map(() => this.buildPreviewFromForm()),
      )
      .subscribe((v) => this.previewSubject.next(v));

    this.load();
  }

  get cards(): FormArray<FormGroup> {
    return this.form.get('cards') as FormArray<FormGroup>;
  }

  get previewBrandName(): string {
    return (
      this.integration?.brand_name?.trim() ||
      this.integration?.organization_name?.trim() ||
      'Сервисный центр'
    );
  }

  get previewAccentColor(): string {
    const color = (this.integration?.accent_color || '').trim();
    if (/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(color)) {
      return color;
    }
    return '#0f766e';
  }

  get portalDomainLabel(): string {
    const domain = (this.integration?.client_domain || '').trim();
    if (!domain) {
      return 'repire-status.ru';
    }
    return domain.replace(/^https?:\/\//i, '').replace(/\/$/, '');
  }

  get portalHref(): string | null {
    const domain = (this.integration?.client_domain || '').trim();
    if (!domain) {
      return null;
    }
    return /^https?:\/\//i.test(domain) ? domain : `https://${domain}`;
  }

  get filledCardsCount(): number {
    const v = this.form?.getRawValue();
    return ((v?.cards || []) as ClientLandingCard[]).filter(
      (c) => (c.title || '').trim() && (c.body || '').trim(),
    ).length;
  }

  private buildPreviewFromForm(): ClientLandingConfig {
    const v = this.form.getRawValue();
    const rawCards = (v.cards || []) as {
      title?: string;
      body?: string;
      icon?: string;
    }[];
    const feature_cards = rawCards
      .filter((c) => (c.title || '').trim() && (c.body || '').trim())
      .map((c) => ({
        title: (c.title || '').trim(),
        body: (c.body || '').trim(),
        icon: c.icon || 'status',
      }));
    return {
      section_eyebrow: (v.landing_section_eyebrow || '').trim(),
      section_title: (v.landing_section_title || '').trim(),
      section_subtitle: (v.landing_section_subtitle || '').trim(),
      feature_cards,
      promo_spotlight: {
        enabled: !!v.promo?.enabled,
        title: (v.promo?.title || '').trim(),
        subtitle: (v.promo?.subtitle || '').trim(),
        body: (v.promo?.body || '').trim(),
        badge: (v.promo?.badge || '').trim(),
        cta_label: (v.promo?.cta_label || '').trim(),
        cta_href: (v.promo?.cta_href || '').trim(),
        image_url: (v.promo?.image_url || '').trim() || null,
      },
    };
  }

  load(): void {
    this.loading = true;
    this.loadError = '';

    forkJoin({
      landing: this.admin.getClientLanding(),
      status: this.admin.getClientSyncStatus().pipe(catchError(() => of(null))),
    })
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: ({ landing, status }) => {
          this.integration = status?.integration ?? this.integration;
          this.patchFromServer(landing);
        },
        error: () => {
          this.loadError = 'Не удалось загрузить настройки лендинга';
          this.snack.open(this.loadError, 'OK', { duration: 5000 });
        },
      });
  }

  private patchFromServer(data: ClientLandingConfig): void {
    this.form.patchValue({
      landing_section_eyebrow: data.section_eyebrow || '',
      landing_section_title: data.section_title || '',
      landing_section_subtitle: data.section_subtitle || '',
      promo: {
        enabled: data.promo_spotlight?.enabled ?? false,
        title: data.promo_spotlight?.title || '',
        subtitle: data.promo_spotlight?.subtitle || '',
        body: data.promo_spotlight?.body || '',
        badge: data.promo_spotlight?.badge || '',
        cta_label: data.promo_spotlight?.cta_label || '',
        cta_href: data.promo_spotlight?.cta_href || '/login?register=1',
        image_url: data.promo_spotlight?.image_url || '',
      },
    });
    const list = data.feature_cards || [];
    for (let i = 0; i < 4; i++) {
      const c = list[i];
      this.cards.at(i).patchValue({
        title: c?.title || '',
        body: c?.body || '',
        icon: c?.icon || 'status',
      });
    }
    this.previewSubject.next(this.buildPreviewFromForm());
    this.form.markAsPristine();
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const v = this.form.getRawValue();
    const cards = ((v.cards || []) as { title?: string; body?: string; icon?: string }[])
      .filter((c) => (c.title || '').trim() && (c.body || '').trim())
      .map((c) => ({
        title: (c.title || '').trim(),
        body: (c.body || '').trim(),
        icon: c.icon || 'status',
      }));
    this.saving = true;
    this.admin
      .patchClientLanding({
        landing_section_eyebrow: (v.landing_section_eyebrow || '').trim(),
        landing_section_title: (v.landing_section_title || '').trim(),
        landing_section_subtitle: (v.landing_section_subtitle || '').trim(),
        feature_cards: cards,
        promo_spotlight: {
          enabled: !!v.promo?.enabled,
          title: (v.promo?.title || '').trim(),
          subtitle: (v.promo?.subtitle || '').trim(),
          body: (v.promo?.body || '').trim(),
          badge: (v.promo?.badge || '').trim(),
          cta_label: (v.promo?.cta_label || '').trim(),
          cta_href: (v.promo?.cta_href || '').trim() || '/login',
          image_url: (v.promo?.image_url || '').trim() || null,
        },
      })
      .pipe(finalize(() => (this.saving = false)))
      .subscribe({
        next: (saved) => {
          this.patchFromServer(saved);
          this.lastSavedAt = new Date();
          this.snack.open('Сохранено и отправлено в клиентский портал', 'OK', { duration: 4000 });
        },
        error: () =>
          this.snack.open('Ошибка сохранения (проверьте интеграцию с порталом)', 'OK', {
            duration: 6000,
          }),
      });
  }

  clearCard(index: number): void {
    this.cards.at(index).patchValue({
      title: '',
      body: '',
      icon: 'status',
    });
    this.cards.at(index).markAsDirty();
  }

  iconPath(icon: string | null | undefined): string {
    return CARD_ICONS.find((item) => item.value === icon)?.path || CARD_ICONS[0].path;
  }

  iconLabel(icon: string | null | undefined): string {
    return CARD_ICONS.find((item) => item.value === icon)?.label || CARD_ICONS[0].label;
  }

  displayFeatureCards(vm: ClientLandingConfig): ClientLandingCard[] {
    return vm.feature_cards.length > 0 ? vm.feature_cards : DEFAULT_FEATURE_CARDS;
  }

  visiblePromo(vm: ClientLandingConfig): ClientLandingPromoSpotlight | null {
    const promo = vm.promo_spotlight;
    if (!promo.enabled) {
      return null;
    }
    if (!(promo.title || promo.body || promo.subtitle)) {
      return null;
    }
    return promo;
  }

  promoCtaLabel(promo: ClientLandingPromoSpotlight): string {
    return promo.cta_label || 'Подробнее';
  }
}

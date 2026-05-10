import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormArray,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { finalize } from 'rxjs';
import { ApiService } from '../../../services/api.service';
import { AdminService } from '../../../services/admin.service';
import { Shop } from '../../../core/models/models';

interface FieldVisitZone {
  id: string;
  name: string;
  price: number;
  geometry: { type: string; coordinates: number[][][] };
}

interface FieldVisitConfig {
  enabled: boolean;
  service_name: string;
  base_price: number;
  out_of_zone_price: number;
  description: string;
  zones: FieldVisitZone[];
  advance_days: number;
}

@Component({
  selector: 'app-field-visit-settings',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatDividerModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  templateUrl: './field-visit-settings.component.html',
  styleUrls: ['./field-visit-settings.component.scss'],
})
export class FieldVisitSettingsComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ApiService);
  private readonly adminService = inject(AdminService);
  private readonly snackBar = inject(MatSnackBar);

  shops: Shop[] = [];
  selectedShopId: number | null = null;
  loading = false;
  saving = false;

  form!: FormGroup;

  private ymapInstances: Map<string, unknown> = new Map();

  ngOnInit(): void {
    this.form = this.fb.group({
      enabled: [false],
      service_name: ['Выезд мастера', Validators.required],
      base_price: [0, [Validators.required, Validators.min(0)]],
      out_of_zone_price: [0, [Validators.required, Validators.min(0)]],
      description: [''],
      advance_days: [1, [Validators.required, Validators.min(0)]],
      zones: this.fb.array([]),
    });

    this.adminService.getShops().subscribe({
      next: (shops) => {
        this.shops = shops;
        if (shops.length > 0) {
          this.selectShop(shops[0].id);
        }
      },
    });
  }

  get zonesArray(): FormArray {
    return this.form.get('zones') as FormArray;
  }

  selectShop(shopId: number): void {
    this.selectedShopId = shopId;
    this.loadConfig(shopId);
  }

  loadConfig(shopId: number): void {
    this.loading = true;
    this.api
      .get<FieldVisitConfig>(`/shops/${shopId}/field-visit`)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (cfg) => this.applyConfig(cfg),
        error: () => {
          // use defaults if endpoint returns 404
          this.applyConfig({
            enabled: false,
            service_name: 'Выезд мастера',
            base_price: 0,
            out_of_zone_price: 0,
            description: '',
            zones: [],
            advance_days: 1,
          });
        },
      });
  }

  private applyConfig(cfg: FieldVisitConfig): void {
    this.form.patchValue({
      enabled: cfg.enabled,
      service_name: cfg.service_name,
      base_price: cfg.base_price,
      out_of_zone_price: cfg.out_of_zone_price,
      description: cfg.description,
      advance_days: cfg.advance_days,
    });
    const arr = this.zonesArray;
    arr.clear();
    (cfg.zones || []).forEach((z) => arr.push(this.zoneGroup(z)));
  }

  private zoneGroup(zone?: Partial<FieldVisitZone>): FormGroup {
    return this.fb.group({
      id: [zone?.id || this.newId()],
      name: [zone?.name || '', Validators.required],
      price: [zone?.price ?? 0, Validators.min(0)],
      geometry: [zone?.geometry || null],
    });
  }

  addZone(): void {
    this.zonesArray.push(this.zoneGroup());
  }

  removeZone(idx: number): void {
    this.zonesArray.removeAt(idx);
  }

  save(): void {
    if (this.form.invalid || !this.selectedShopId) return;
    this.saving = true;
    const payload = this.form.getRawValue();
    this.api
      .patch<FieldVisitConfig>(`/shops/${this.selectedShopId}/field-visit`, payload)
      .pipe(finalize(() => (this.saving = false)))
      .subscribe({
        next: () =>
          this.snackBar.open('Настройки выезда сохранены', 'OK', { duration: 3000 }),
        error: () =>
          this.snackBar.open('Ошибка сохранения', 'OK', { duration: 3000 }),
      });
  }

  initMap(zoneIdx: number): void {
    const containerId = `ymap-zone-${zoneIdx}`;
    const key = containerId;
    if (this.ymapInstances.has(key)) return;

    const ymapsUrl = 'https://api-maps.yandex.ru/2.1/?lang=ru_RU';
    const existing = document.querySelector('script[data-ymap-crm]');
    const trySetup = () => this.setupZoneMap(containerId, zoneIdx);

    if (existing) {
    const ymaps = (window as unknown as Record<string, unknown>)['ymaps'];
    if (ymaps) {
      trySetup();
    } else {
      existing.addEventListener('load', trySetup);
    }
      return;
    }

    const script = document.createElement('script');
    script.src = ymapsUrl;
    script.setAttribute('data-ymap-crm', '1');
    script.onload = trySetup;
    document.head.appendChild(script);
  }

  private setupZoneMap(containerId: string, zoneIdx: number): void {
    const ymaps = (window as unknown as Record<string, unknown>)['ymaps'] as {
      ready: (fn: () => void) => void;
      Map: new (id: string, opts: unknown) => {
        events: { add(e: string, fn: (ev: unknown) => void): void };
        geoObjects: { add(o: unknown): void; removeAll(): void };
      };
      Polygon: new (coords: unknown, props: unknown, opts: unknown) => unknown;
      DrawingControl: unknown;
    };
    if (!ymaps) return;

    ymaps.ready(() => {
      const container = document.getElementById(containerId);
      if (!container) return;
      const map = new ymaps.Map(containerId, { center: [55.76, 37.64], zoom: 10 });
      this.ymapInstances.set(containerId, map);

      const zoneGroup = this.zonesArray.at(zoneIdx) as FormGroup;
      const existing = zoneGroup.get('geometry')?.value as FieldVisitZone['geometry'] | null;

      if (existing?.type === 'Polygon' && existing.coordinates?.length) {
        const coords = existing.coordinates[0].map(([lng, lat]: number[]) => [lat, lng]);
        const poly = new ymaps.Polygon([coords], {}, { fillColor: 'rgba(15,118,110,0.2)', strokeColor: '#0f766e', strokeWidth: 2 });
        map.geoObjects.add(poly);
      }

      // Simple polygon drawing via click to add points (minimal impl)
      let drawCoords: [number, number][] = [];
      map.events.add('click', (ev: unknown) => {
        const coords = (ev as { get(k: string): [number, number] }).get('coords');
        drawCoords.push(coords);
        map.geoObjects.removeAll();
        if (drawCoords.length >= 3) {
          const poly = new ymaps.Polygon(
            [drawCoords],
            { hintContent: 'Зона обслуживания' },
            { fillColor: 'rgba(15,118,110,0.2)', strokeColor: '#0f766e', strokeWidth: 2 }
          );
          map.geoObjects.add(poly);
          const geoJson = {
            type: 'Polygon' as const,
            coordinates: [drawCoords.map(([lat, lng]) => [lng, lat])],
          };
          zoneGroup.patchValue({ geometry: geoJson });
        }
      });
    });
  }

  clearZoneMap(zoneIdx: number): void {
    const zoneGroup = this.zonesArray.at(zoneIdx) as FormGroup;
    zoneGroup.patchValue({ geometry: null });
    const containerId = `ymap-zone-${zoneIdx}`;
    const map = this.ymapInstances.get(containerId) as { geoObjects: { removeAll(): void } } | undefined;
    if (map) map.geoObjects.removeAll();
    this.ymapInstances.delete(containerId);
  }

  private newId(): string {
    return Math.random().toString(36).slice(2, 9);
  }

  shopName(id: number): string {
    return this.shops.find((s) => s.id === id)?.name ?? `Магазин #${id}`;
  }
}

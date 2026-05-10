import * as L from 'leaflet';
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

  private leafletMaps: Map<string, L.Map> = new Map();
  private drawCoords: Map<string, L.LatLng[]> = new Map();

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
    const containerId = `leaflet-zone-${zoneIdx}`;
    if (this.leafletMaps.has(containerId)) return;

    const container = document.getElementById(containerId);
    if (!container) return;

    // Fix Leaflet icon paths for Angular builds
    const iconDefault = L.icon({
      iconUrl: 'assets/leaflet/marker-icon.png',
      iconRetinaUrl: 'assets/leaflet/marker-icon-2x.png',
      shadowUrl: 'assets/leaflet/marker-shadow.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41],
    });
    L.Marker.prototype.options.icon = iconDefault;

    const map = L.map(containerId, { center: [55.76, 37.64], zoom: 10 });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);
    this.leafletMaps.set(containerId, map);

    const zoneGroup = this.zonesArray.at(zoneIdx) as FormGroup;
    const existing = zoneGroup.get('geometry')?.value as FieldVisitZone['geometry'] | null;
    let polygon: L.Polygon | null = null;

    if (existing?.type === 'Polygon' && existing.coordinates?.length) {
      const latlngs = existing.coordinates[0].map(([lng, lat]: number[]) => [lat, lng] as [number, number]);
      polygon = L.polygon(latlngs, { color: '#0f766e', fillOpacity: 0.2 }).addTo(map);
      map.fitBounds(polygon.getBounds());
    }

    const coords: L.LatLng[] = [];
    this.drawCoords.set(containerId, coords);

    map.on('click', (e: L.LeafletMouseEvent) => {
      coords.push(e.latlng);
      if (polygon) { map.removeLayer(polygon); polygon = null; }
      if (coords.length >= 3) {
        polygon = L.polygon(coords, { color: '#0f766e', fillOpacity: 0.2 })
          .bindTooltip('Зона обслуживания')
          .addTo(map);
        const geoJson = {
          type: 'Polygon' as const,
          coordinates: [coords.map((ll) => [ll.lng, ll.lat])],
        };
        zoneGroup.patchValue({ geometry: geoJson });
      }
    });
  }

  clearZoneMap(zoneIdx: number): void {
    const zoneGroup = this.zonesArray.at(zoneIdx) as FormGroup;
    zoneGroup.patchValue({ geometry: null });
    const containerId = `leaflet-zone-${zoneIdx}`;
    const map = this.leafletMaps.get(containerId);
    if (map) { map.eachLayer((l) => { if (l instanceof L.Polygon) map.removeLayer(l); }); }
    const coords = this.drawCoords.get(containerId);
    if (coords) coords.length = 0;
  }

  private newId(): string {
    return Math.random().toString(36).slice(2, 9);
  }

  shopName(id: number): string {
    return this.shops.find((s) => s.id === id)?.name ?? `Магазин #${id}`;
  }
}

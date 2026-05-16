import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import {
  InventoryProductGroup,
  InventoryService,
  Supplier
} from '../../../services/inventory.service';

@Component({
  selector: 'app-inventory-item-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatAutocompleteModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule
  ],
  templateUrl: './inventory-item-form.component.html',
  styleUrl: './inventory-item-form.component.scss'
})
export class InventoryItemFormComponent implements OnInit {
  loading = false;
  suppliers: Supplier[] = [];
  productGroups: InventoryProductGroup[] = [];

  itemTypes = [
    { value: 'component', label: 'Комплектующие' },
    { value: 'accessory', label: 'Аксессуары' },
    { value: 'consumable', label: 'Расходные материалы' },
    { value: 'tool', label: 'Инструменты' },
    { value: 'software', label: 'Программное обеспечение' },
    { value: 'service', label: 'Услуга' }
  ];

  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private inventoryService: InventoryService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {
    this.form = this.fb.group({
      name: ['', Validators.required],
      sku: ['', Validators.required],
      item_type: ['component', Validators.required],
      category_name: ['Запчасти', Validators.required],
      procurement_group_name: [''],
      primary_supplier_id: [null as number | null],
      purchase_price: [0, [Validators.required, Validators.min(0)]],
      selling_price: [0, [Validators.required, Validators.min(0)]],
      unit: ['шт', Validators.required],
      barcode: [''],
      description: ['']
    });
  }

  ngOnInit(): void {
    this.inventoryService.getSuppliers().subscribe((suppliers) => {
      this.suppliers = suppliers;
    });
    this.inventoryService.getProductGroups().subscribe((groups) => {
      this.productGroups = groups;
    });
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    const barcode = (value.barcode || '').trim();
    this.loading = true;

    this.inventoryService.quickCreateItem({
      name: (value.name || '').trim(),
      sku: (value.sku || '').trim(),
      item_type: value.item_type || 'component',
      category_name: (value.category_name || 'Запчасти').trim(),
      procurement_group_name: (value.procurement_group_name || '').trim() || undefined,
      primary_supplier_id: value.primary_supplier_id || undefined,
      purchase_price: Number(value.purchase_price || 0),
      selling_price: Number(value.selling_price || 0),
      unit: value.unit || 'шт',
      barcodes: barcode ? [barcode] : [],
      description: (value.description || '').trim()
    }).subscribe({
      next: () => {
        this.snackBar.open('Товар добавлен', 'Закрыть', { duration: 3000 });
        this.router.navigate(['/inventory']);
      },
      error: (error) => {
        const message = error?.error?.error || 'Не удалось добавить товар';
        this.snackBar.open(message, 'Закрыть', { duration: 4000 });
        this.loading = false;
      }
    });
  }

  cancel(): void {
    this.router.navigate(['/inventory']);
  }
}

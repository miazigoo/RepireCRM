import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ThemeService, Theme } from '../../../services/theme.service';

@Component({
  selector: 'app-theme-selector',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatGridListModule,
    MatTooltipModule
  ],
  templateUrl: './theme-selector.component.html',
  styleUrl: './theme-selector.component.css'
})
export class ThemeSelectorComponent implements OnInit {
  themes: Theme[] = [];
  currentTheme: Theme;

  constructor(private themeService: ThemeService) {
    this.currentTheme = this.themeService.getCurrentTheme();
  }

  ngOnInit(): void {
    this.themes = this.themeService.getAvailableThemes();

    this.themeService.currentTheme$.subscribe(theme => {
      this.currentTheme = theme;
    });
  }

  selectTheme(theme: Theme): void {
    this.themeService.setTheme(theme.id);
  }

  isCurrentTheme(theme: Theme): boolean {
    return this.currentTheme.id === theme.id;
  }

  getPreviewStyle(theme: Theme): Record<string, string> {
    return {
      background: `linear-gradient(135deg, ${theme.colors.primary}, ${theme.colors.accent})`
    };
  }

  getThemeColors(theme: Theme): Array<{ name: string; value: string }> {
    return [
      { name: 'Основной', value: theme.colors.primary },
      { name: 'Вторичный', value: theme.colors.secondary },
      { name: 'Акцент', value: theme.colors.accent },
      { name: 'Ошибка', value: theme.colors.warn },
      { name: 'Фон', value: theme.colors.background },
      { name: 'Поверхность', value: theme.colors.surface }
    ];
  }
}

import { Component, OnInit, AfterViewInit, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, DashboardData } from '../../services/api.service';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="cn-page-header">
      <h1 class="cn-page-title">Developer Behaviour Dashboard</h1>
      <p class="cn-page-subtitle">Analyze repository activity and developer patterns</p>
    </div>

    <!-- Repo Selector -->
    <div class="cn-card">
      <div class="cn-form-group">
        <label class="cn-form-label">Select Repository</label>
        <select class="cn-input cn-select" [(ngModel)]="selectedRepoId" (change)="loadDashboard()">
          <option *ngFor="let repo of repositories" [value]="repo.id">{{ repo.owner }}/{{ repo.name }}</option>
        </select>
      </div>
    </div>

    <!-- Loading -->
    <div *ngIf="loading" class="cn-state-info">
      <h5>Loading</h5>
      <p>Fetching repository data...</p>
    </div>

    <!-- Error -->
    <div *ngIf="error" class="cn-state-error">
      <h5>Error</h5>
      <p>{{ error }}</p>
    </div>

    <!-- Dashboard Content -->
    <div *ngIf="data" class="cn-dashboard-grid">
      <!-- Repo Info -->
      <div class="cn-card cn-card-borderless">
        <h2 class="cn-h3">{{ data.repository.owner }}/{{ data.repository.name }}</h2>
        <p class="cn-text-lg">{{ data.repository.description || 'No description' }}</p>
        <p><span class="cn-chip cn-chip-brand">{{ data.repository.language || 'N/A' }}</span></p>
      </div>

      <!-- Features Stat Tiles -->
      <div class="cn-stat-grid">
        <div class="cn-stat-tile accent-brand">
          <div class="cn-stat-value">{{ data.features.commits_per_day }}</div>
          <div class="cn-stat-label">Commits / Day</div>
        </div>
        <div class="cn-stat-tile accent-accent">
          <div class="cn-stat-value">{{ data.features.active_days }}</div>
          <div class="cn-stat-label">Active Days</div>
        </div>
        <div class="cn-stat-tile accent-success">
          <div class="cn-stat-value">{{ data.features.weekend_activity }}</div>
          <div class="cn-stat-label">Weekend Commits</div>
        </div>
        <div class="cn-stat-tile accent-warning">
          <div class="cn-stat-value">{{ data.features.code_change_volume }}</div>
          <div class="cn-stat-label">Code Changes</div>
        </div>
      </div>

      <!-- Productivity Indicators -->
      <div class="cn-card cn-card-borderless">
        <h2 class="cn-h4">Productivity Indicators</h2>
        <ul class="cn-metric-list">
          <li class="cn-metric-item">
            <span class="cn-metric-label">Commits / Day</span>
            <span class="cn-chip cn-chip-brand">{{ data.productivity.indicators.commits_per_day }}</span>
          </li>
          <li class="cn-metric-item">
            <span class="cn-metric-label">Active Day Ratio</span>
            <span class="cn-chip cn-chip-brand">{{ (data.productivity.indicators.active_day_ratio * 100).toFixed(1) }}%</span>
          </li>
          <li class="cn-metric-item">
            <span class="cn-metric-label">Consistency Score</span>
            <span class="cn-chip cn-chip-success">{{ (data.productivity.indicators.consistency_score * 100).toFixed(1) }}%</span>
          </li>
          <li class="cn-metric-item">
            <span class="cn-metric-label">Avg Changes / Commit</span>
            <span class="cn-chip cn-chip-info">{{ data.productivity.indicators.avg_code_changes_per_commit }}</span>
          </li>
        </ul>
      </div>

      <!-- Timeline Chart -->
      <div class="cn-chart-card">
        <h2 class="cn-h4">Commit Timeline</h2>
        <div class="cn-chart-container">
          <canvas #timelineCanvas></canvas>
        </div>
      </div>

      <!-- Time of Day Chart -->
      <div class="cn-chart-card">
        <h2 class="cn-h4">Time of Day Distribution</h2>
        <div class="cn-chart-container">
          <canvas #todCanvas></canvas>
        </div>
      </div>
    </div>
  `,
  styles: [``],
})
export class DashboardComponent implements OnInit, AfterViewInit {
  @ViewChild('timelineCanvas') timelineCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('todCanvas') todCanvas!: ElementRef<HTMLCanvasElement>;

  repositories: any[] = [];
  selectedRepoId: number | null = null;
  data: DashboardData | null = null;
  loading = false;
  error: string | null = null;

  private timelineChart: Chart | null = null;
  private todChart: Chart | null = null;

  constructor(private api: ApiService, private router: Router) {}

  ngOnInit() {
    this.loadRepositories();
  }

  ngAfterViewInit() {
    // Charts will be drawn when data loads
  }

  loadRepositories() {
    this.loading = true;
    this.api.listRepositories().subscribe({
      next: (repos) => {
        this.repositories = repos;
        if (repos.length > 0 && !this.selectedRepoId) {
          this.selectedRepoId = repos[0].id;
          this.loadDashboard();
        }
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = 'Failed to load repositories';
      },
    });
  }

  loadDashboard() {
    if (!this.selectedRepoId) return;
    this.loading = true;
    this.error = null;

    this.api.getDashboard(this.selectedRepoId).subscribe({
      next: (d) => {
        this.data = d;
        this.loading = false;
        this.drawCharts();
      },
      error: () => {
        this.loading = false;
        this.error = 'Failed to load dashboard data';
      },
    });
  }

  private drawCharts() {
    if (!this.data) return;

    // Timeline chart
    const timelineData = Object.entries(this.data.timeline);
    if (this.timelineCanvas && timelineData.length > 0) {
      const ctx = this.timelineCanvas.nativeElement.getContext('2d');
      if (ctx) {
        if (this.timelineChart) this.timelineChart.destroy();
        this.timelineChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: timelineData.map(([d]) => d),
            datasets: [{
              label: 'Commits per Day',
              data: timelineData.map(([, c]) => c),
              borderColor: '#1e3a8a',
              backgroundColor: 'rgba(30, 58, 138, 0.2)',
              tension: 0.4,
              fill: true,
            }],
          },
          options: { responsive: true, maintainAspectRatio: false },
        } as ChartConfiguration);
      }
    }

    // Time of day chart
    const tod = this.data.features.time_of_day_distribution;
    if (this.todCanvas && tod) {
      const ctx = this.todCanvas.nativeElement.getContext('2d');
      if (ctx) {
        const hours = Array.from({ length: 24 }, (_, i) => i.toString());
        const values = hours.map((h) => tod[h] || 0);
        if (this.todChart) this.todChart.destroy();
        this.todChart = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: hours,
            datasets: [{
              label: 'Commits by Hour',
              data: values,
              backgroundColor: '#0f766e',
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { x: { title: { display: true, text: 'Hour of Day' } }, y: { title: { display: true, text: 'Commits' } } },
          },
        } as ChartConfiguration);
      }
    }
  }
}
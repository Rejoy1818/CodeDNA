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
    <div class="dashboard">
      <h2 class="mb-4">Developer Behaviour Dashboard</h2>

      <!-- Repo Selector -->
      <div class="card mb-4">
        <div class="card-body">
          <h5 class="card-title">Select Repository</h5>
          <select class="form-select" [(ngModel)]="selectedRepoId" (change)="loadDashboard()">
            <option *ngFor="let repo of repositories" [value]="repo.id">{{ repo.owner }}/{{ repo.name }}</option>
          </select>
        </div>
      </div>

      <!-- Loading -->
      <div *ngIf="loading" class="text-center py-4">
        <div class="spinner-border"></div> Loading...
      </div>

      <!-- Error -->
      <div *ngIf="error" class="alert alert-danger">{{ error }}</div>

      <!-- Dashboard Content -->
      <div *ngIf="data" class="row">
        <!-- Repo Info -->
        <div class="col-md-6">
          <div class="card mb-4">
            <div class="card-body">
              <h5 class="card-title">{{ data.repository.owner }}/{{ data.repository.name }}</h5>
              <p class="card-text">{{ data.repository.description || 'No description' }}</p>
              <small class="text-muted">Language: {{ data.repository.language || 'N/A' }}</small>
            </div>
          </div>
        </div>

        <!-- Features Cards -->
        <div class="col-md-6">
          <div class="row">
            <div class="col-6">
              <div class="card stat-card mb-3">
                <div class="card-body">
                  <div class="stat-value">{{ data.features.commits_per_day }}</div>
                  <div class="stat-label">Commits / Day</div>
                </div>
              </div>
            </div>
            <div class="col-6">
              <div class="card stat-card mb-3">
                <div class="card-body">
                  <div class="stat-value">{{ data.features.active_days }}</div>
                  <div class="stat-label">Active Days</div>
                </div>
              </div>
            </div>
            <div class="col-6">
              <div class="card stat-card mb-3">
                <div class="card-body">
                  <div class="stat-value">{{ data.features.weekend_activity }}</div>
                  <div class="stat-label">Weekend Commits</div>
                </div>
              </div>
            </div>
            <div class="col-6">
              <div class="card stat-card mb-3">
                <div class="card-body">
                  <div class="stat-value">{{ data.features.code_change_volume }}</div>
                  <div class="stat-label">Code Changes</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Productivity Indicators -->
        <div class="col-md-6">
          <div class="card mb-4">
            <div class="card-body">
              <h5 class="card-title">Productivity Indicators</h5>
              <ul class="list-group list-group-flush">
                <li class="list-group-item d-flex justify-content-between">
                  <span>Commits / Day</span>
                  <span class="badge bg-primary">{{ data.productivity.indicators.commits_per_day }}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                  <span>Active Day Ratio</span>
                  <span class="badge bg-info">{{ (data.productivity.indicators.active_day_ratio * 100).toFixed(1) }}%</span>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                  <span>Consistency Score</span>
                  <span class="badge bg-warning">{{ (data.productivity.indicators.consistency_score * 100).toFixed(1) }}%</span>
                </li>
                <li class="list-group-item d-flex justify-content-between">
                  <span>Avg Changes / Commit</span>
                  <span class="badge bg-secondary">{{ data.productivity.indicators.avg_code_changes_per_commit }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Timeline Chart -->
        <div class="col-md-6">
          <div class="card mb-4">
            <div class="card-body">
              <h5 class="card-title">Commit Timeline</h5>
              <div class="chart-container">
                <canvas #timelineCanvas></canvas>
              </div>
            </div>
          </div>
        </div>

        <!-- Time of Day Chart -->
        <div class="col-md-6">
          <div class="card mb-4">
            <div class="card-body">
              <h5 class="card-title">Time of Day Distribution</h5>
              <div class="chart-container">
                <canvas #todCanvas></canvas>
              </div>
            </div>
          </div>
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
              borderColor: '#667eea',
              backgroundColor: 'rgba(102, 126, 234, 0.2)',
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
              backgroundColor: '#764ba2',
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
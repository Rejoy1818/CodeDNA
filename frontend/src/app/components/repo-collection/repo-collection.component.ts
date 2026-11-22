import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-repo-collection',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="cn-card">
      <div class="cn-section">
        <h2 class="cn-section-title">Collect Repository Data</h2>
        <form (ngSubmit)="onSubmit()" #form="ngForm">
          <div class="cn-form-group">
            <label class="cn-form-label">Repository Owner</label>
            <input type="text" class="cn-input" name="owner" [(ngModel)]="model.owner" required />
          </div>
          <div class="cn-form-group">
            <label class="cn-form-label">Repository Name</label>
            <input type="text" class="cn-input" name="repo" [(ngModel)]="model.repo" required />
          </div>
          <div class="cn-form-group">
            <label class="cn-form-label">Max Commits</label>
            <input type="number" class="cn-input" name="max_commits" [(ngModel)]="model.max_commits" value="500" />
          </div>
          <button type="submit" class="cn-btn cn-btn-accent" [disabled]="loading">Collect Data</button>
        </form>

        <div *ngIf="result" class="cn-state-box cn-state-success">
          <h5>Collection Complete</h5>
          <p><strong>{{ result.repository.owner }}/{{ result.repository.name }}</strong></p>
          <p>Commits collected: {{ result.commit_count }}</p>
        </div>

        <div *ngIf="error" class="cn-state-box cn-state-error">{{ error }}</div>
      </div>
    </div>
  `,
})
export class RepoCollectionComponent {
  model = { owner: '', repo: '', max_commits: 500 };
  loading = false;
  result: any = null;
  error: string | null = null;

  constructor(private api: ApiService) {}

  onSubmit() {
    this.loading = true;
    this.error = null;
    this.result = null;

    this.api.collectRepository(this.model).subscribe({
      next: (r) => {
        this.result = r;
        this.loading = false;
      },
      error: () => {
        this.error = 'Failed to collect repository data';
        this.loading = false;
      },
    });
  }
}
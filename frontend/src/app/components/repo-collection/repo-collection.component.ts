import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-repo-collection',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <div class="card-body">
        <h2 class="card-title mb-4">Collect Repository Data</h2>
        <form (ngSubmit)="onSubmit()" #form="ngForm">
          <div class="mb-3">
            <label class="form-label">Repository Owner</label>
            <input type="text" class="form-control" name="owner" [(ngModel)]="model.owner" required />
          </div>
          <div class="mb-3">
            <label class="form-label">Repository Name</label>
            <input type="text" class="form-control" name="repo" [(ngModel)]="model.repo" required />
          </div>
          <div class="mb-3">
            <label class="form-label">Max Commits</label>
            <input type="number" class="form-control" name="max_commits" [(ngModel)]="model.max_commits" value="500" />
          </div>
          <button type="submit" class="btn btn-primary" [disabled]="loading">Collect Data</button>
        </form>

        <div *ngIf="result" class="mt-4 alert alert-success">
          <h5>Collection Complete</h5>
          <p><strong>{{ result.repository.owner }}/{{ result.repository.name }}</strong></p>
          <p>Commits collected: {{ result.commit_count }}</p>
        </div>

        <div *ngIf="error" class="mt-4 alert alert-danger">{{ error }}</div>
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
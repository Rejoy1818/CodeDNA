import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { RepoCollectionComponent } from './components/repo-collection/repo-collection.component';
import { CodeClassificationComponent } from './components/code-classification/code-classification.component';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'collect', component: RepoCollectionComponent },
  { path: 'classify', component: CodeClassificationComponent },
  { path: '**', redirectTo: '/dashboard' },
];
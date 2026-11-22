import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <nav class="cn-sidebar">
      <div class="sidebar-brand">
        <a class="sidebar-brand-link" routerLink="/dashboard">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
          <span class="sidebar-brand-text">CodeDNA</span>
        </a>
      </div>
      <nav class="sidebar-nav">
        <ul class="sidebar-nav-list">
          <li class="sidebar-nav-item">
            <a class="sidebar-nav-link" routerLink="/dashboard" routerLinkActive="active" routerLinkActiveOptions="{exact: true}">
              <span class="nav-item-text">Dashboard</span>
            </a>
          </li>
          <li class="sidebar-nav-item">
            <a class="sidebar-nav-link" routerLink="/collect" routerLinkActive="active">
              <span class="nav-item-text">Collect Repository</span>
            </a>
          </li>
          <li class="sidebar-nav-item">
            <a class="sidebar-nav-link" routerLink="/classify" routerLinkActive="active">
              <span class="nav-item-text">AI Code Classification</span>
            </a>
          </li>
        </ul>
      </nav>
    </nav>
  `,
})
export class SidebarComponent {}
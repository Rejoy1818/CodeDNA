import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <nav class="cn-navbar">
      <div class="cn-container">
        <a class="cn-navbar-brand" routerLink="/dashboard">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
          <span>CodeDNA</span>
        </a>
        <button class="cn-navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="cn-navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="cn-navbar-nav">
            <li class="cn-nav-item">
              <a class="cn-nav-link" routerLink="/dashboard" routerLinkActive="active" routerLinkActiveOptions="{exact: true}">Dashboard</a>
            </li>
            <li class="cn-nav-item">
              <a class="cn-nav-link" routerLink="/collect" routerLinkActive="active">Collect Repository</a>
            </li>
            <li class="cn-nav-item">
              <a class="cn-nav-link" routerLink="/classify" routerLinkActive="active">AI Code Classification</a>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  `,
})
export class NavbarComponent {}
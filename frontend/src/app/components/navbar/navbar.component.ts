import { Component } from '@angular/core';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [],
  template: `
    <header class="cn-navbar">
      <div class="cn-container">
        <div class="cn-navbar-brand">
          <a routerLink="/dashboard">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            <span>CodeDNA</span>
          </a>
        </div>
      </div>
    </header>
  `,
})
export class NavbarComponent {}
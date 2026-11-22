import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavbarComponent } from './components/navbar/navbar.component';
import { SidebarComponent } from './components/sidebar/sidebar.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavbarComponent, SidebarComponent],
  template: `
    <app-sidebar></app-sidebar>
    <main class="cn-page">
      <app-navbar></app-navbar>
      <div class="cn-container">
        <router-outlet></router-outlet>
      </div>
    </main>
  `,
})
export class AppComponent {
  title = 'CodeDNA';
}
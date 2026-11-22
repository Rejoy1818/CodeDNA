import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavbarComponent } from './components/navbar/navbar.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavbarComponent],
  template: `
    <app-navbar></app-navbar>
    <main class="cn-page">
      <div class="cn-container">
        <router-outlet></router-outlet>
      </div>
    </main>
  `,
})
export class AppComponent {
  title = 'CodeDNA';
}
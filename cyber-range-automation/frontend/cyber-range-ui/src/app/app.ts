import { Component, signal } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { NavbarComponent } from './navbar/navbar';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, NavbarComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('cyber-range-ui');

  constructor(private router: Router) {}

  shouldShowNavbar(): boolean {
    return !this.router.url.includes('/login') && !this.router.url.includes('/register');
  }
}
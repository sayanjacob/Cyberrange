import { CommonModule } from '@angular/common';
import { Component, computed } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-navbar',
  templateUrl: './navbar.html',
  styleUrls: ['./navbar.css'],
  standalone: true,
  imports: [CommonModule]
})
export class NavbarComponent {
  home() {
    this.router.navigate(['/home']);
  }
  isLoggedIn = sessionStorage.getItem('isLoggedIn') === 'true' || false;
  username = sessionStorage.getItem('username');
  constructor(private router: Router) { }

  logout() {
    sessionStorage.removeItem('username');
    sessionStorage.removeItem('isLoggedIn');
    this.router.navigate(['/']);
  }

  login() {
    this.router.navigate(['/login']);
  }
  register() {
    this.router.navigate(['/register']);
  }
}
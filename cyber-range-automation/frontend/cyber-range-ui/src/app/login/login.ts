import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login',
  templateUrl: './login.html',
  styleUrls: ['./login.css'],
  standalone: true,
  imports: [FormsModule,CommonModule]
})
export class Login {
  username = '';
  password = '';
  loginError = false; // Track invalid credentials

  constructor(private router: Router) { }

  login() {
    // Only allow login if username is 'JaikIype' and password is 'jaik'
    if (this.username === 'JaikIype' && this.password === 'jaik') {
      sessionStorage.setItem("isLoggedIn", "true");
      sessionStorage.setItem("username", this.username);
      this.loginError = false;
      this.router.navigate(['/home']);
    } else {
      this.loginError = true;
      console.log('Invalid credentials:', this.username, this.password);
    }
  }

  goToRegister() {
    this.router.navigate(['/register']);
  }
}

import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-login',
  templateUrl: './login.html',
  styleUrls: ['./login.css'],
  standalone: true,
  imports: [FormsModule]
})
export class Login {
  username = '';
  password = '';

  constructor(private router: Router) { }

  login() {
    // Add your login logic here
    console.log('Username:', this.username);
    console.log('Password:', this.password);
    // For now, just navigate to the home page
    sessionStorage.setItem("isLoggedIn", "true");
    sessionStorage.setItem("username", this.username);
    this.router.navigate(['/home']);
  }

  goToRegister() {
    this.router.navigate(['/register']);
  }
}

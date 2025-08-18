import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-register',
  templateUrl: './register.html',
  styleUrls: ['./register.css'],
  standalone: true,
  imports: [FormsModule]
})
export class RegisterComponent {
  username = '';
  password = '';
  confirmPassword = '';

  constructor(private router: Router) { }

  register() {
    // Add your registration logic here
    console.log('Username:', this.username);
    console.log('Password:', this.password);
    console.log('Confirm Password:', this.confirmPassword);
    // For now, just navigate to the login page
    this.router.navigate(['/login']);
  }

  goToLogin() {
    this.router.navigate(['/login']);
  }
}
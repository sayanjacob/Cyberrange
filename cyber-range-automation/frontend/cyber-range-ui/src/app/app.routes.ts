import { Routes } from '@angular/router';
import { Home } from './home/home';
import { ScenarioDetailsComponent } from './scenario-details/scenario-details';
import { Login } from './login/login';
import { RegisterComponent } from './register/register';
import { Landing } from './landing/landing';

export const routes: Routes = [
    {
        path: '',
        component: Landing
    },
    {
        path: 'login',
        component: Login
    },
    {
        path: 'register',
        component: RegisterComponent
    },
    {
        path: 'home',
        component: Home
    },
    {
        path: 'scenario/:id',
        component: ScenarioDetailsComponent
    }
];
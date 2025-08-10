import { Routes } from '@angular/router';
import { Home } from './home/home';
import { ScenarioDetailsComponent } from './scenario-details/scenario-details';

export const routes: Routes = [
    {
        path: '',
        component: Home
    },
    {
        path: 'scenario/:id',
        component: ScenarioDetailsComponent
    }
];
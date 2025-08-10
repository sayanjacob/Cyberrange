import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ScenarioService } from '../scenario.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Scenario } from '../home/home';

@Component({
  selector: 'app-scenario-details',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './scenario-details.html',
  styleUrls: ['./scenario-details.css']
})
export class ScenarioDetailsComponent implements OnInit {

  scenario: (Scenario & { steps: { id: number, title: string, description: string, completed: boolean }[] }) | undefined;

  constructor(
    private route: ActivatedRoute,
    private scenarioService: ScenarioService
  ) { }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    this.scenario = this.scenarioService.getScenario(id);
  }

}

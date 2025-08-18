import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { ScenarioService } from '../scenario.service';
import { NavbarComponent } from "../navbar/navbar";

export interface Scenario {
  id: string;
  title: string;
  description: string;
  time: number;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  locked: boolean;
  category: string;
  imageUrl?: string;
  stars?: number;
  completedBy?: number;
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [FormsModule, CommonModule, RouterModule, NavbarComponent],
  templateUrl: './home.html', // Make sure this file exists
  styleUrls: ['./home.css']   // Make sure this file exists
})
export class Home implements OnInit {

  searchTerm: string = '';
  selectedLength: string = '';
  selectedDifficulty: string = '';
  selectedCategory: string = '';

  lengths: string[] = ['15 mins', '30 mins', '45 mins', '60 mins', '90+ mins'];
  difficulties: string[] = ['Easy', 'Medium', 'Hard'];
  categories: string[] = ['Network Security', 'Web Security', 'Forensics', 'Malware Analysis', 'Social Engineering'];

  scenarios: Scenario[] = [];

  constructor(private router: Router,
    private scenarioService: ScenarioService) {
    console.log('🔧 Home Component Constructor');
    this.initializeScenarios();
  }


  async ngOnInit(): Promise<void> {
    console.log('🚀 Home Component OnInit - Scenarios:', this.scenarios.length);
    const status = await this.scenarioService.getStatus();
    console.log('🔄 Status fetched:', status);
    // Safety check
    if (!this.scenarios || this.scenarios.length === 0) {
      console.log('⚠️ No scenarios found, reinitializing...');
      this.initializeScenarios();
    }
  }

  private initializeScenarios(): void {
    this.scenarios = this.scenarioService.getAllScenarios();
    console.log('✅ Scenarios initialized:', this.scenarios.length);
  }

  // Add this method for the debug template
  forceLoadScenarios(): void {
    console.log('🔄 Force reloading scenarios...');
    this.initializeScenarios();
  }

  get totalScenarios(): number {
    return this.scenarios ? this.scenarios.length : 0;
  }

  get unlockedScenarios(): number {
    return this.scenarios ? this.scenarios.filter(s => !s.locked).length : 0;
  }

  get filteredScenariosCount(): number {
    return this.filteredScenarios().length;
  }

  filteredScenarios(): Scenario[] {
    if (!this.scenarios || this.scenarios.length === 0) {
      return [];
    }

    return this.scenarios.filter(scenario => {
      const matchesSearch = !this.searchTerm ||
        scenario.title.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        scenario.description.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        scenario.category.toLowerCase().includes(this.searchTerm.toLowerCase());

      const matchesLength = !this.selectedLength ||
        `${scenario.time} mins` === this.selectedLength ||
        (this.selectedLength === '90+ mins' && scenario.time >= 90);

      const matchesDifficulty = !this.selectedDifficulty ||
        scenario.difficulty === this.selectedDifficulty;

      const matchesCategory = !this.selectedCategory ||
        scenario.category === this.selectedCategory;

      return matchesSearch && matchesLength && matchesDifficulty && matchesCategory;
    });
  }

  getDifficultyBadgeClass(difficulty: string): string {
    switch (difficulty) {
      case 'Easy': return 'bg-success';
      case 'Medium': return 'bg-warning text-dark';
      case 'Hard': return 'bg-danger';
      default: return 'bg-secondary';
    }
  }

  getScenarioImage(scenario: Scenario): string {
    // Generate different colored gradients based on category
    const colors: { [key: string]: string } = {
      'Network Security': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      'Web Security': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
      'Forensics': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
      'Malware Analysis': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
      'Social Engineering': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
    };

    return colors[scenario.category] || colors['Network Security'];
  }

  onScenarioClick(scenario: Scenario): void {
    if (!scenario.locked) {
      console.log('🎯 Navigating to scenario:', scenario.id);
      this.router.navigate(['/scenario', scenario.id]);
    } else {
      console.log('🔒 Scenario is locked:', scenario.id);
    }
  }

  clearFilters(): void {
    this.searchTerm = '';
    this.selectedLength = '';
    this.selectedDifficulty = '';
    this.selectedCategory = '';
  }

  getStars(rating: number): number[] {
    return new Array(5).fill(0).map((_, i) => i < rating ? 1 : 0);
  }
}
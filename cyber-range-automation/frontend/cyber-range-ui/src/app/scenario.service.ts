import { Injectable } from '@angular/core';
import { Scenario } from './home/home';

@Injectable({
  providedIn: 'root'
})
export class ScenarioService {

  scenarios: (Scenario & { steps: {id: number, title: string, description: string, completed: boolean}[] })[] = [
    {
      id: 'apt28-part1',
      title: 'APT28: Link to Trouble - Part 1',
      description: 'Here at TryGovMe, our partners have been consistently targeted by APT28 over the past few weeks and we are now under pressure to investigate.',
      time: 15,
      difficulty: 'Easy',
      locked: false,
      category: 'Network Security',
      stars: 3,
      completedBy: 1250,
      steps: [
        { id: 1, title: 'Initial Compromise', description: 'Gain initial access to the target system.', completed: false },
        { id: 2, title: 'Establish Foothold', description: 'Deploy persistence mechanisms.', completed: false },
        { id: 3, title: 'Privilege Escalation', description: 'Gain higher privileges on the system.', completed: false },
      ]
    },
    {
      id: 'apt28-part2',
      title: 'APT28: Link to Trouble - Part 2',
      description: 'Our worst fears have been confirmed. We have discovered that TryGovMe has also been compromised by APT28. It is time to investigate.',
      time: 15,
      difficulty: 'Easy',
      locked: false,
      category: 'Network Security',
      stars: 3,
      completedBy: 980,
      steps: [
        { id: 1, title: 'Analyze the malware', description: 'Reverse engineer the malware to understand its capabilities.', completed: false },
        { id: 2, title: 'Identify the C2 server', description: 'Find the command and control server.', completed: false },
      ]
    },
    {
      id: 'apt28-part3',
      title: 'APT28: Link to Trouble - Part 3',
      description: 'Our team has determined that the attacker has successfully established communication with a host within the network infrastructure.',
      time: 15,
      difficulty: 'Easy',
      locked: false,
      category: 'Network Security',
      stars: 3,
      completedBy: 750,
      steps: []
    },
    {
      id: 'apt28-part4',
      title: 'APT28: Link to Trouble - Part 4',
      description: 'APT28 continues to move deeper, step by step gaining a clearer understanding of what the TryGovMe organisation is built upon.',
      time: 15,
      difficulty: 'Easy',
      locked: true,
      category: 'Network Security',
      stars: 3,
      completedBy: 450,
      steps: []
    },
    {
      id: 'web-exploit-1',
      title: 'SQL Injection Masterclass',
      description: 'Learn advanced SQL injection techniques and how to exploit vulnerable web applications in a controlled environment.',
      time: 45,
      difficulty: 'Medium',
      locked: false,
      category: 'Web Security',
      stars: 4,
      completedBy: 2100,
      steps: []
    },
    {
      id: 'forensics-1',
      title: 'Digital Crime Scene Investigation',
      description: 'Analyze digital evidence from a compromised system and reconstruct the attack timeline using forensic tools.',
      time: 60,
      difficulty: 'Hard',
      locked: false,
      category: 'Forensics',
      stars: 5,
      completedBy: 320,
      steps: []
    },
    {
      id: 'malware-1',
      title: 'Reverse Engineering Challenge',
      description: 'Dissect malicious software to understand its behavior and develop countermeasures.',
      time: 90,
      difficulty: 'Hard',
      locked: true,
      category: 'Malware Analysis',
      stars: 5,
      completedBy: 180,
      steps: []
    },
    {
      id: 'social-eng-1',
      title: 'Phishing Campaign Analysis',
      description: 'Investigate a sophisticated phishing campaign and trace the attack vectors used by threat actors.',
      time: 30,
      difficulty: 'Medium',
      locked: false,
      category: 'Social Engineering',
      stars: 4,
      completedBy: 890,
      steps: []
    }
  ];

  constructor() { }

  getScenario(id: string | null) {
    if (!id) {
      return undefined;
    }
    return this.scenarios.find(s => s.id === id);
  }
}
import { Injectable } from '@angular/core';
import { Scenario } from './home/home';
import axios from 'axios';

@Injectable({
  providedIn: 'root'
})
export class ScenarioService {

  scenarios: (Scenario & { steps: {id: number, title: string, description: string, completed: boolean}[] })[] = [
    {
      id: 'phishing-email-1',
      title: 'Phishing Email Scenario',
      description: 'Investigate a phishing email to identify and analyze a potential threat. This scenario will guide you through the process of examining the email headers, identifying the sender, and analyzing the content for malicious links or attachments.',
      time: 20,
      difficulty: 'Easy',
      locked: false,
      category: 'Social Engineering',
      stars: 3,
      completedBy: 0,
      steps: [
        { id: 1, title: 'Check mail', description: 'cat /var/mail/vagrant', completed: false },
        { id: 2, title: 'Note phishing link', description: 'http://192.168.56.11/malicious_link.html', completed: false },
        { id: 3, title: 'Open in browser or use wget', description: 'Open the link in a browser or use wget to download the file.', completed: false },
        { id: 4, title: 'Check if file fake_invoice.exe dropped', description: 'Check if the file fake_invoice.exe was dropped in the system.', completed: false },
        { id: 5, title: 'Review logs', description: '/var/log/syslog, /tmp, processes', completed: false },
        { id: 6, title: 'Optional: Use net-tools to inspect connections', description: 'Use net-tools to inspect network connections.', completed: false }
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
    }
   
    
  ];

  constructor() { }
  private baseUrl = 'http://localhost:5000/api'; // Flask backend URL

  getScenario(id: string | null) {
    if (!id) {
      return undefined;
    }
    return this.scenarios.find(s => s.id === id);
  }

  async getStatus(){
    const response =await axios.get(`${this.baseUrl}/health`);
    //console.log('🔄 Status response:', response.data);
    return response.data;
  }


  getAllScenarios() {
    return this.scenarios;
  }
}
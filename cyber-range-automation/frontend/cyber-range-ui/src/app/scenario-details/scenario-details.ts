import { Component, OnInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ScenarioService } from '../scenario.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http';
import { Subscription, interval } from 'rxjs';

// Socket.IO client interface (simplified for basic usage without the library)
interface Socket {
  on(event: string, callback: (data: any) => void): void;
  emit(event: string, data?: any): void;
  disconnect(): void;
}

// Mock socket.io function for environments where it's not available
declare const io: ((url: string, options?: any) => Socket) | undefined;

interface GuacSession {
  userType: 'victim' | 'attacker';
  url: SafeResourceUrl | null;
  isActive: boolean;
  windowSize: 'small' | 'medium' | 'large' | 'fullscreen';
  isMinimized: boolean;
  position: { x: number; y: number };
  token?: string;
  hasValidToken?: boolean;
  connectionUrl?: string;
  lastActivity?: Date;
}

interface GuacUserConfig {
  username: string;
  display_name: string;
  description: string;
  color_theme: string;
  connection_id: string;
  has_active_token: boolean;
}

interface SystemStatus {
  session: any;
  guac_users: { [key: string]: GuacUserConfig };
  scenarios: any;
}

interface ScenarioResult {
  id: string;
  action: string;
  code: number;
  stdout: string;
  stderr: string;
  success: boolean;
  timestamp: string;
}

@Component({
  selector: 'app-scenario-details',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './scenario-details.html',
  styleUrls: ['./scenario-details.css']
})
export class ScenarioDetailsComponent implements OnInit, OnDestroy {
  @ViewChild('victimFrame', { static: false }) victimFrame!: ElementRef<HTMLIFrameElement>;
  @ViewChild('attackerFrame', { static: false }) attackerFrame!: ElementRef<HTMLIFrameElement>;

  // Configuration
  private readonly API_BASE = 'http://localhost:5000/api';
  
  // Component state
  scenario: any;
  isLoading = false;
  isConnectingAll = false;
  error: string | null = null;
  systemStatus: SystemStatus | null = null;
  
  // Multi-user session management
  sessions: { [key: string]: GuacSession } = {
    victim: {
      userType: 'victim',
      url: null,
      isActive: false,
      windowSize: 'medium',
      isMinimized: false,
      position: { x: 50, y: 50 },
      hasValidToken: false
    },
    attacker: {
      userType: 'attacker',
      url: null,
      isActive: false,
      windowSize: 'medium',
      isMinimized: false,
      position: { x: 350, y: 50 },
      hasValidToken: false
    }
  };

  // Available user types
  availableUsers: ('victim' | 'attacker')[] = ['victim', 'attacker'];
  userConfigs: { [key: string]: GuacUserConfig } = {};
  
  // Dragging state
  isDragging = false;
  dragTarget: string | null = null;
  dragOffset = { x: 0, y: 0 };

  // WebSocket connection
  private socket: Socket | null = null;
  private subscriptions: Subscription[] = [];
  private statusCheckInterval: Subscription | null = null;

  // Activity tracking
  private lastUserActivity = new Date();
  private activityCheckInterval: Subscription | null = null;

  constructor(
    private route: ActivatedRoute,
    private scenarioService: ScenarioService,
    private sanitizer: DomSanitizer,
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    console.log('Scenario ID:', id);
    this.scenario = this.scenarioService.getScenario(id);
    console.log('Scenario details:', this.scenario);
    
    this.initializeComponent();
  }

  ngOnDestroy(): void {
    this.cleanup();
  }

  private async initializeComponent() {
    try {
      // Initialize WebSocket connection
      this.initializeWebSocket();
      
      // Load system status
      await this.loadSystemStatus();
      
      // Start periodic status checks
      this.startStatusChecks();
      
      // Start activity tracking
      this.startActivityTracking();
      
    } catch (error) {
      console.error('Error initializing component:', error);
      this.error = 'Failed to initialize lab environment. Please refresh the page.';
    }
  }

  private initializeWebSocket() {
    try {
      // Check if socket.io is available
      if (typeof io === 'undefined') {
        console.warn('Socket.IO not available, real-time features disabled');
        return;
      }

      this.socket = io(this.API_BASE.replace('/api', ''), {
        withCredentials: true,
        transports: ['websocket', 'polling']
      });

      this.socket.on('connect', () => {
        console.log('WebSocket connected');
        this.socket?.emit('join_session', { session_id: null }); // Backend will use session from cookie
      });

      this.socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
      });

      this.socket.on('user_connected', (data: any) => {
        console.log('User connected:', data);
        this.handleUserConnected(data);
      });

      this.socket.on('user_disconnected', (data: any) => {
        console.log('User disconnected:', data);
        this.handleUserDisconnected(data);
      });

      this.socket.on('bulk_connect_complete', (data: any) => {
        console.log('Bulk connect complete:', data);
        this.handleBulkConnectComplete(data);
      });

      this.socket.on('bulk_disconnect_complete', (data: any) => {
        console.log('Bulk disconnect complete:', data);
        this.handleBulkDisconnectComplete(data);
      });

      this.socket.on('scenario_update', (data: any) => {
        console.log('Scenario update:', data);
        this.handleScenarioUpdate(data);
      });

      this.socket.on('session_reset', (data: any) => {
        console.log('Session reset:', data);
        this.handleSessionReset(data);
      });

    } catch (error) {
      console.error('Error initializing WebSocket:', error);
    }
  }

  private async loadSystemStatus() {
    try {
      const response = await this.http.get<SystemStatus>(`${this.API_BASE}/status`).toPromise();
      if (response) {
        this.systemStatus = response;
        this.userConfigs = response.guac_users;
        this.availableUsers = Object.keys(response.guac_users).filter((user): user is 'victim' | 'attacker' => 
          user === 'victim' || user === 'attacker'
        );
        
        // Update session token status
        Object.keys(this.sessions).forEach(userType => {
          const config = this.userConfigs[userType];
          if (config) {
            this.sessions[userType].hasValidToken = config.has_active_token;
          }
        });
        
        console.log('System status loaded:', response);
      }
    } catch (error) {
      console.error('Error loading system status:', error);
    }
  }

  private startStatusChecks() {
    // Check system status every 30 seconds
    this.statusCheckInterval = interval(30000).subscribe(() => {
      this.loadSystemStatus();
    });
  }

  private startActivityTracking() {
    // Track user activity to keep sessions alive
    const updateActivity = () => {
      this.lastUserActivity = new Date();
      Object.values(this.sessions).forEach(session => {
        if (session.isActive) {
          session.lastActivity = new Date();
        }
      });
    };

    // Listen for user interactions
    ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'].forEach(event => {
      document.addEventListener(event, updateActivity, true);
    });

    // Periodic activity check every 5 minutes
    this.activityCheckInterval = interval(300000).subscribe(() => {
      this.checkSessionHealth();
    });
  }

  private async checkSessionHealth() {
    for (const userType of this.availableUsers) {
      const session = this.sessions[userType];
      if (session.isActive && session.lastActivity) {
        const timeSinceActivity = new Date().getTime() - session.lastActivity.getTime();
        
        // If no activity for 15 minutes, validate token
        if (timeSinceActivity > 15 * 60 * 1000) {
          await this.validateSessionToken(userType);
        }
      }
    }
  }

  private async validateSessionToken(userType: 'victim' | 'attacker') {
    try {
      const response = await this.http.get(`${this.API_BASE}/guac/connections/${userType}`).toPromise();
      console.log(`Token validation for ${userType}:`, response);
    } catch (error) {
      console.warn(`Token validation failed for ${userType}, may need to reconnect:`, error);
      this.sessions[userType].hasValidToken = false;
    }
  }

  // Helper method to calculate time since last activity
  getTimeSince(date: Date): string {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ago`;
    } else if (minutes > 0) {
      return `${minutes}m ago`;
    } else {
      return 'just now';
    }
  }

  async runScenario() {
    try {
      this.isLoading = true;
      this.error = null;
      
      console.log('Starting scenario...');
      
      // Start the scenario backend first
      await this.startScenarioBackend();
      
      this.isLoading = false;
      
    } catch (error) {
      console.error('Error running scenario:', error);
      this.error = 'Failed to start scenario. Please try again.';
      this.isLoading = false;
    }
  }

  async startScenarioBackend() {
    const scenarioId = this.route.snapshot.paramMap.get('id');
    if (!scenarioId) return;

    try {
      const response = await this.http.post<ScenarioResult>(
        `${this.API_BASE}/scenarios/${scenarioId}/start`,
        {}
      ).toPromise();

      if (response) {
        console.log('Scenario started:', response);
        
        if (!response.success) {
          throw new Error(`Scenario start failed: ${response.stderr || response.stdout}`);
        }
      }
      
    } catch (error) {
      console.error('Error starting scenario backend:', error);
      throw error;
    }
  }

  async startGuacSession(userType: 'victim' | 'attacker') {
    try {
      this.error = null;
      this.sessions[userType].isActive = true; // Set immediately for UI feedback
      
      // Get token from backend
      const tokenResponse = await this.http.post<any>(
        `${this.API_BASE}/guac/token/${userType}`,
        {}
      ).toPromise();
      
      if (tokenResponse) {
        const session = this.sessions[userType];
        session.token = tokenResponse.token;
        session.connectionUrl = tokenResponse.connection_url;
        session.hasValidToken = true;
        session.lastActivity = new Date();
        
        // Use auto-login URL for iframe
        const autoLoginUrl = `${this.API_BASE.replace('/api', '')}/api/guac/auto-login/${userType}`;
        session.url = this.sanitizer.bypassSecurityTrustResourceUrl(autoLoginUrl);
        session.isMinimized = false;
        
        console.log(`Started ${userType} session:`, tokenResponse);
        
        // Update user config
        if (this.userConfigs[userType]) {
          this.userConfigs[userType].has_active_token = true;
        }
      }
      
    } catch (error) {
      console.error(`Error starting ${userType} session:`, error);
      this.error = `Failed to start ${userType} session. Please try again.`;
      this.sessions[userType].isActive = false;
    }
  }

  async closeGuacSession(userType: 'victim' | 'attacker') {
    try {
      // Call disconnect endpoint
      await this.http.post(`${this.API_BASE}/guac/disconnect/${userType}`, {}).toPromise();
      
      // Update local state
      const session = this.sessions[userType];
      session.isActive = false;
      session.url = null;
      session.isMinimized = false;
      session.token = undefined;
      session.hasValidToken = false;
      session.connectionUrl = undefined;
      
      // Update user config
      if (this.userConfigs[userType]) {
        this.userConfigs[userType].has_active_token = false;
      }
      
      console.log(`Closed ${userType} session`);
      
    } catch (error) {
      console.error(`Error closing ${userType} session:`, error);
      // Still update UI even if backend call fails
      this.sessions[userType].isActive = false;
      this.sessions[userType].url = null;
    }
  }

  async connectAllSessions() {
    try {
      this.isConnectingAll = true;
      this.error = null;
      
      // Call bulk connect endpoint
      const response = await this.http.post<any>(`${this.API_BASE}/guac/connect-all`, {}).toPromise();
      
      if (response) {
        console.log('Bulk connect response:', response);
        
        // Handle successful connections
        Object.keys(response.results).forEach(userType => {
          if (userType === 'victim' || userType === 'attacker') {
            const result = response.results[userType];
            const session = this.sessions[userType];
            
            session.isActive = true;
            session.token = result.token;
            session.connectionUrl = result.connection_url;
            session.hasValidToken = true;
            session.lastActivity = new Date();
            
            // Use auto-login URL for iframe
            const autoLoginUrl = `${this.API_BASE.replace('/api', '')}/api/guac/auto-login/${userType}`;
            session.url = this.sanitizer.bypassSecurityTrustResourceUrl(autoLoginUrl);
            session.isMinimized = false;
            
            // Update user config
            if (this.userConfigs[userType]) {
              this.userConfigs[userType].has_active_token = true;
            }
          }
        });
        
        // Handle errors
        if (Object.keys(response.errors).length > 0) {
          const errorMessages = Object.entries(response.errors)
            .map(([userType, error]: [string, any]) => `${userType}: ${error.error}`)
            .join(', ');
          this.error = `Some connections failed: ${errorMessages}`;
        }
      }
      
    } catch (error) {
      console.error('Error connecting all sessions:', error);
      this.error = 'Failed to connect all sessions. Please try individually.';
    } finally {
      this.isConnectingAll = false;
    }
  }

  async disconnectAllSessions() {
    try {
      this.isConnectingAll = true;
      
      // Call bulk disconnect endpoint
      const response = await this.http.post<any>(`${this.API_BASE}/guac/disconnect-all`, {}).toPromise();
      
      if (response) {
        console.log('Bulk disconnect response:', response);
        
        // Update all sessions
        Object.keys(this.sessions).forEach(userType => {
          const session = this.sessions[userType];
          session.isActive = false;
          session.url = null;
          session.isMinimized = false;
          session.token = undefined;
          session.hasValidToken = false;
          session.connectionUrl = undefined;
          
          // Update user config
          if (this.userConfigs[userType]) {
            this.userConfigs[userType].has_active_token = false;
          }
        });
      }
      
    } catch (error) {
      console.error('Error disconnecting all sessions:', error);
      this.error = 'Failed to disconnect all sessions.';
    } finally {
      this.isConnectingAll = false;
    }
  }

  toggleSessionSize(userType: 'victim' | 'attacker') {
    const session = this.sessions[userType];
    const sizes: ('small' | 'medium' | 'large' | 'fullscreen')[] = ['small', 'medium', 'large', 'fullscreen'];
    const currentIndex = sizes.indexOf(session.windowSize);
    const nextIndex = (currentIndex + 1) % sizes.length;
    session.windowSize = sizes[nextIndex];
  }

  setSessionSize(userType: 'victim' | 'attacker', size: 'small' | 'medium' | 'large' | 'fullscreen') {
    this.sessions[userType].windowSize = size;
  }

  toggleMinimize(userType: 'victim' | 'attacker') {
    this.sessions[userType].isMinimized = !this.sessions[userType].isMinimized;
  }

  refreshSession(userType: 'victim' | 'attacker') {
    const frameRef = userType === 'victim' ? this.victimFrame : this.attackerFrame;
    
    if (frameRef && frameRef.nativeElement) {
      const currentSrc = frameRef.nativeElement.src;
      frameRef.nativeElement.src = '';
      setTimeout(() => {
        frameRef.nativeElement.src = currentSrc;
      }, 100);
    }
  }

  openInNewTab(userType: 'victim' | 'attacker') {
    const session = this.sessions[userType];
    const url = session.connectionUrl || `${this.API_BASE.replace('/api', '')}/api/guac/auto-login/${userType}`;
    window.open(url, `_blank_${userType}`, 'width=1200,height=800,scrollbars=yes,resizable=yes');
  }

  // Dragging functionality
  startDrag(event: MouseEvent, userType: 'victim' | 'attacker') {
    const session = this.sessions[userType];
    if (session.windowSize === 'fullscreen') return;
    
    event.preventDefault();
    this.isDragging = true;
    this.dragTarget = userType;
    this.dragOffset = {
      x: event.clientX - session.position.x,
      y: event.clientY - session.position.y
    };
    
    // Add global mouse event listeners
    const handleMouseMove = (e: MouseEvent) => this.onDrag(e);
    const handleMouseUp = (e: MouseEvent) => this.stopDrag(e, handleMouseMove, handleMouseUp);
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }

  onDrag(event: MouseEvent) {
    if (!this.isDragging || !this.dragTarget) return;
    
    event.preventDefault();
    const session = this.sessions[this.dragTarget];
    
    session.position = {
      x: event.clientX - this.dragOffset.x,
      y: event.clientY - this.dragOffset.y
    };
    
    // Constrain to viewport with some padding
    const maxX = window.innerWidth - 400;
    const maxY = window.innerHeight - 300;
    
    session.position.x = Math.max(0, Math.min(session.position.x, maxX));
    session.position.y = Math.max(0, Math.min(session.position.y, maxY));
  }

  stopDrag(event: MouseEvent, mouseMoveHandler: (e: MouseEvent) => void, mouseUpHandler: (e: MouseEvent) => void) {
    this.isDragging = false;
    this.dragTarget = null;
    document.removeEventListener('mousemove', mouseMoveHandler);
    document.removeEventListener('mouseup', mouseUpHandler);
  }

  getSessionStyle(userType: 'victim' | 'attacker') {
    const session = this.sessions[userType];
    
    if (session.windowSize === 'fullscreen') {
      return {
        'position': 'fixed',
        'top': '0px',
        'left': '0px',
        'width': '100vw',
        'height': '100vh',
        'z-index': '9999'
      };
    }
    
    return {
      'position': 'fixed',
      'top': session.position.y + 'px',
      'left': session.position.x + 'px',
      'z-index': '1000'
    };
  }

  getActiveSessionsCount(): number {
    return Object.values(this.sessions).filter(session => session.isActive).length;
  }

  getUserTypeColor(userType: 'victim' | 'attacker'): string {
    const config = this.userConfigs[userType];
    return config ? config.color_theme : (userType === 'attacker' ? '#e74c3c' : '#3498db');
  }

  getUserTypeIcon(userType: 'victim' | 'attacker'): string {
    return userType === 'attacker' ? 'bi-shield-exclamation' : 'bi-shield-check';
  }

  getUserDisplayName(userType: 'victim' | 'attacker'): string {
    const config = this.userConfigs[userType];
    return config ? config.display_name : userType;
  }

  getUserDescription(userType: 'victim' | 'attacker'): string {
    const config = this.userConfigs[userType];
    return config ? config.description : '';
  }

  // WebSocket event handlers
  private handleUserConnected(data: any) {
    if (data.user_type && (data.user_type === 'victim' || data.user_type === 'attacker')) {
      const session = this.sessions[data.user_type];
      session.hasValidToken = true;
      session.lastActivity = new Date();
      
      if (this.userConfigs[data.user_type]) {
        this.userConfigs[data.user_type].has_active_token = true;
      }
      
      this.cdr.detectChanges();
    }
  }

  private handleUserDisconnected(data: any) {
    if (data.user_type && (data.user_type === 'victim' || data.user_type === 'attacker')) {
      const session = this.sessions[data.user_type];
      session.hasValidToken = false;
      
      if (this.userConfigs[data.user_type]) {
        this.userConfigs[data.user_type].has_active_token = false;
      }
      
      this.cdr.detectChanges();
    }
  }

  private handleBulkConnectComplete(data: any) {
    this.isConnectingAll = false;
    
    // Update sessions based on results
    Object.keys(data.results).forEach(userType => {
      if (userType === 'victim' || userType === 'attacker') {
        const session = this.sessions[userType];
        session.hasValidToken = true;
        session.lastActivity = new Date();
        
        if (this.userConfigs[userType]) {
          this.userConfigs[userType].has_active_token = true;
        }
      }
    });
    
    this.cdr.detectChanges();
  }

  private handleBulkDisconnectComplete(data: any) {
    this.isConnectingAll = false;
    
    // Update all sessions
    Object.keys(this.sessions).forEach(userType => {
      const session = this.sessions[userType];
      session.hasValidToken = false;
      
      if (this.userConfigs[userType]) {
        this.userConfigs[userType].has_active_token = false;
      }
    });
    
    this.cdr.detectChanges();
  }

  private handleScenarioUpdate(data: any) {
    console.log('Scenario update received:', data);
    // You can add UI notifications here
  }

  private handleSessionReset(data: any) {
    console.log('Session reset:', data);
    // Reload system status after session reset
    this.loadSystemStatus();
  }

  private cleanup() {
    // Cleanup WebSocket
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    
    // Cleanup subscriptions
    this.subscriptions.forEach(sub => sub.unsubscribe());
    
    if (this.statusCheckInterval) {
      this.statusCheckInterval.unsubscribe();
    }
    
    if (this.activityCheckInterval) {
      this.activityCheckInterval.unsubscribe();
    }
    
    // Remove event listeners
    ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'].forEach(event => {
      document.removeEventListener(event, () => {}, true);
    });
  }
  
}
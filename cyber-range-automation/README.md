# Cyber Range Automation

This project provides a framework for automating the setup and management of cyber ranges for security training and research. It utilizes Docker to create isolated environments for various scenarios.

## 🚀 Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   [Docker](https://docs.docker.com/get-docker/)
*   [Docker Compose](https://docs.docker.com/compose/install/)

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/sayanjacob/Cyberrange.git
    ```
2.  Navigate to the `cyber-range-automation` directory:
    ```bash
    cd Cyberrange/cyber-range-automation
    ```
3.  Build and run the Docker containers:
    ```bash
    docker-compose up -d
    ```

##  сценарии

This cyber range comes with a pre-built scenario to simulate a phishing attack.

### 🛡️ Phishing Email Scenario

*   **Objective:** Simulate a phishing email, malware drop, and basic incident response.
*   **Machines:**
    *   **Attacker:** A Kali Linux container.
    *   **Victim:** A vulnerable container.

To run this scenario, follow the instructions in the scenario's documentation.

## 🐳 Docker Usage

*   **Build and run the containers:**
    ```bash
    docker-compose up -d
    ```
*   **Stop the containers:**
    ```bash
    docker-compose down
    ```
*   **Access the Kali Linux container:**
    ```bash
    docker-compose exec kali /bin/bash
    ```

## 🤝 Contributing

Contributions are welcome! Please read the [contributing guidelines](.github/CONTRIBUTING.md) for this project.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

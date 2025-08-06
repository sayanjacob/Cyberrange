#!/bin/bash
sudo apt update && sudo apt install -y mailutils curl wget net-tools
echo "From: admin@example.com
To: victim@example.com
Subject: Urgent Invoice

Please download your invoice: http://192.168.56.11/malicious_link.html

Thanks" > /tmp/email.txt

sudo cp /tmp/email.txt /var/mail/vagrant
echo "Email sent to victim's mailbox.""
echo "This script sets up a phishing email scenario. Ensure to run it on the attacker machine
and replace the IP address with the actual attacker machine's IP."
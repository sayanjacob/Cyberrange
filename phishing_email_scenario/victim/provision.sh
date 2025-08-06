#!/bin/bash
sudo apt-get update
sudo apt-get install -y mailutils

# Create a fake email
echo "From: billing@megacorp.com
To: user@example.com
Subject: Urgent: Unpaid Invoice

Dear User,

Please find attached your unpaid invoice. Failure to settle this immediately may result in service suspension.

http://192.168.56.11/malicious_link.html

Sincerely,

MegaCorp Billing" > /tmp/phishing_email.txt

# Deliver the email to the vagrant user
sudo mv /tmp/phishing_email.txt /var/mail/vagrant
sudo chown vagrant:mail /var/mail/vagrant

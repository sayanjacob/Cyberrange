#!/bin/bash

sudo apt update && sudo apt install -y python3

# Create directory and copy file
mkdir -p /home/vagrant/www
cp /vagrant/www/fake_invoice.exe /home/vagrant/www/

# Ensure shared_logs is writable
sudo chown vagrant:vagrant /home/vagrant/shared_logs

# Start server and log to shared_logs
nohup python3 -m http.server 80 --directory /home/vagrant/www > /home/vagrant/shared_logs/http.log 2>&1 &
echo "Attacker server started on port 80, serving files from /home/vagrant/www"
echo "Logs are being written to /home/vagrant/shared_logs/http.log"
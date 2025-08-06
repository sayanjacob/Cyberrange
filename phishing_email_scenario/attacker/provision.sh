#!/bin/bash
sudo apt update && sudo apt install -y python3
mkdir -p /home/vagrant/www
cp /vagrant/evidence/malicious_link.html /home/vagrant/www/index.html
cp /vagrant/evidence/fake_invoice.exe /home/vagrant/www/fake_invoice.exe

cd /home/vagrant/www
nohup python3 -m http.server 80 &
echo "Web server started. Access the malicious link at http://<attacker_ip>/index.html"
echo "Fake invoice available at http://<attacker_ip>/fake_invoice.exe"
echo "Ensure to replace <attacker_ip> with the actual IP address of the attacker machine
#!/bin/bash
sudo apt-get update
sudo apt-get install -y apache2
sudo cp /vagrant/evidence/malicious_link.html /var/www/html/
sudo cp /vagrant/evidence/fake_invoice.exe /var/www/html/
sudo systemctl restart apache2
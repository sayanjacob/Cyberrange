#!/bin/bash

# Update system
apt-get update && apt-get upgrade -y

# Install XFCE desktop and xrdp for remote access
apt-get install -y xfce4 xfce4-goodies xrdp

# Set xfce as default session for xrdp
echo xfce4-session > /home/vagrant/.xsession
chown vagrant:vagrant /home/vagrant/.xsession

# Enable xrdp service
systemctl enable xrdp
systemctl restart xrdp

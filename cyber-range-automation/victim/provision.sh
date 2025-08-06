#!/bin/bash

# Update system
apt-get update && apt-get upgrade -y

# Install XFCE desktop and XRDP
DEBIAN_FRONTEND=noninteractive apt-get install -y xfce4 xfce4-goodies xrdp

# Set xfce as default session for XRDP
echo xfce4-session > /home/vagrant/.xsession
chown vagrant:vagrant /home/vagrant/.xsession

# Ensure XRDP uses correct session
echo "exec startxfce4" | tee /etc/skel/.xsession

# Add vagrant user to ssl-cert group for XRDP
adduser vagrant ssl-cert

# Enable and restart xrdp
systemctl enable xrdp
systemctl restart xrdp

# Allow RDP through firewall if ufw is enabled (optional)
if command -v ufw &> /dev/null; then
  ufw allow 3389
fi

# Print status
echo "XRDP setup complete. The VM is ready for remote desktop login."

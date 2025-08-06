#!/bin/bash

set -e
set -u

echo "🔄 Updating system..."
apt-get update && apt-get upgrade -y

echo "📦 Installing GUI, VNC Server, and Web VNC Client..."
DEBIAN_FRONTEND=noninteractive apt-get install -y xfce4 xfce4-goodies tightvncserver x11vnc novnc websockify

# Setup VNC password for user 'vagrant'
echo "🔐 Setting VNC password for vagrant..."
sudo -u vagrant mkdir -p /home/vagrant/.vnc
echo "vagrant" | vncpasswd -f > /home/vagrant/.vnc/passwd
chown vagrant:vagrant /home/vagrant/.vnc/passwd
chmod 600 /home/vagrant/.vnc/passwd

# VNC startup script
echo "🚀 Creating xstartup..."
cat << EOF > /home/vagrant/.vnc/xstartup
#!/bin/bash
xrdb \$HOME/.Xresources
startxfce4 &
EOF
chown vagrant:vagrant /home/vagrant/.vnc/xstartup
chmod +x /home/vagrant/.vnc/xstartup

# VNC systemd service
echo "⚙️ Configuring systemd for VNC..."
cat << EOF > /etc/systemd/system/vncserver@.service
[Unit]
Description=Start TightVNC server at startup for user vagrant on display :%i
After=network.target

[Service]
Type=forking
User=vagrant
Group=vagrant
WorkingDirectory=/home/vagrant
PIDFile=/home/vagrant/.vnc/%H:%i.pid
ExecStartPre=-/usr/bin/vncserver -kill :%i > /dev/null 2>&1
ExecStart=/usr/bin/vncserver -depth 24 -geometry 1280x800 :%i
ExecStop=/usr/bin/vncserver -kill :%i

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vncserver@1.service
systemctl restart vncserver@1.service

# noVNC systemd service
echo "🌐 Setting up noVNC..."
cat << EOF > /etc/systemd/system/novnc.service
[Unit]
Description=noVNC Service
After=network.target

[Service]
Type=simple
User=vagrant
ExecStart=/usr/bin/websockify --web=/usr/share/novnc/ 6080 localhost:5901

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable novnc.service
systemctl restart novnc.service

# Optional: Open firewall if UFW is active
if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
  echo "🌐 Allowing port 6080 through UFW..."
  ufw allow 6080
fi

echo "✅ Setup complete!"
echo "👉 Access the VM GUI at: http://192.168.1.6:6080/vnc.html"
echo "🔐 VNC Password: vagrant"

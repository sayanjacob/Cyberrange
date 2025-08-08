#!/bin/bash

set -e
set -u

echo "🌀 Updating Kali..."
apt-get update && apt-get upgrade -y

echo "🧠 Installing XFCE Desktop + LightDM..."
DEBIAN_FRONTEND=noninteractive apt-get install -y kali-desktop-xfce lightdm

echo "🌐 Installing Firefox..."
apt-get install -y firefox-esr

echo "📡 Installing VNC and noVNC..."
apt-get install -y tightvncserver x11vnc novnc websockify

echo "🔐 Setting VNC password..."
sudo -u vagrant mkdir -p /home/vagrant/.vnc
sudo -u vagrant bash -c "echo 'vagrant' | vncpasswd -f > /home/vagrant/.vnc/passwd"
chmod 600 /home/vagrant/.vnc/passwd

# VNC startup
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
Description=VNC Server for user vagrant on display :%i
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

echo "✅ Kali Attacker VNC setup complete"
echo "👉 Access noVNC at: http://localhost:6082/vnc.html"
echo "🔐 VNC Password: vagrant"

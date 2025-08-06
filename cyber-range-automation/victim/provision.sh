#!/bin/bash

set -e  # Exit on any error
set -u  # Treat unset variables as errors

echo "🔄 Updating system..."
apt-get update && apt-get upgrade -y

echo "📦 Installing GUI, VNC Server, and Web VNC Client..."
DEBIAN_FRONTEND=noninteractive apt-get install -y xfce4 xfce4-goodies tightvncserver novnc websockify

# --- VNC Server Setup ---
echo "🔐 Setting up VNC password for vagrant user..."
mkdir -p /home/vagrant/.vnc
# Set a default password 'vagrant'
echo "vagrant" | vncpasswd -f > /home/vagrant/.vnc/passwd
chown -R vagrant:vagrant /home/vagrant/.vnc
chmod 0600 /home/vagrant/.vnc/passwd

echo "🚀 Configuring VNC startup script..."
cat << EOF > /home/vagrant/.vnc/xstartup
#!/bin/bash
xrdb $HOME/.Xresources
startxfce4 &
EOF
chown vagrant:vagrant /home/vagrant/.vnc/xstartup
chmod +x /home/vagrant/.vnc/xstartup

echo "⚙️ Creating systemd service for VNC Server..."
cat << EOF > /etc/systemd/system/vncserver@.service
[Unit]
Description=Start TightVNC server at startup for user vagrant on display :%i
After=syslog.target network.target

[Service]
Type=forking
User=vagrant
Group=vagrant
WorkingDirectory=/home/vagrant
PAMName=login
PIDFile=/home/vagrant/.vnc/%H:%i.pid
ExecStartPre=-/usr/bin/vncserver -kill :%i > /dev/null 2>&1
ExecStartPre=-/bin/rm -f /tmp/.X%i-lock /tmp/.X11-unix/X%i
ExecStart=/usr/bin/vncserver -depth 24 -geometry 1280x800 :%i
ExecStop=/usr/bin/vncserver -kill :%i

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Enabling VNC service for display :1..."
systemctl daemon-reload
systemctl enable vncserver@1.service
systemctl restart vncserver@1.service # Restart to apply changes immediately

# --- noVNC Setup ---
echo "🌐 Creating systemd service for noVNC..."
cat << EOF > /etc/systemd/system/novnc.service
[Unit]
Description=noVNC Service
After=network.target

[Service]
Type=simple
User=vagrant
ExecStart=/usr/bin/websockify -D --web=/usr/share/novnc/ 6080 localhost:5901

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Enabling and starting noVNC service..."
systemctl daemon-reload
systemctl enable novnc.service
systemctl restart novnc.service # Restart to apply changes immediately

echo "🌐 Configuring firewall (if ufw is active)..."
if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 6080
  echo "✅ Port 6080 allowed in UFW."
else
  echo "ℹ️ UFW not active or not installed; skipping firewall config."
fi

echo "✅ VNC and noVNC setup complete."
echo "🖥️ To access the GUI, browse to http://<victim-ip>:6080/vnc.html"

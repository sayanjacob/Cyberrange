#!/bin/bash

set -e
set -u

e#!/bin/bash

echo "🌀 Updating system..."
apt-get update && apt-get upgrade -y

echo "🧠 Installing Xubuntu Desktop (XFCE)..."
DEBIAN_FRONTEND=noninteractive apt-get install -y xubuntu-desktop lightdm

echo "🌐 Replacing Snap Firefox with .deb version..."
add-apt-repository ppa:mozillateam/ppa -y
apt-get update

# Pin to ensure apt uses .deb not Snap version
cat <<EOF > /etc/apt/preferences.d/mozilla-firefox
Package: firefox*
Pin: release o=LP-PPA-mozillateam
Pin-Priority: 1001
EOF

apt-get remove -y firefox
apt-get install -y firefox

echo "📡 Installing VNC and noVNC dependencies..."
apt-get install -y tightvncserver x11vnc novnc websockify

echo "🔧 Configuring VNC server..."

echo "🔐 Setting VNC password for vagrant..."
sudo -u vagrant mkdir -p /home/vagrant/.vnc
sudo -u vagrant bash -c "echo 'vagrant' | vncpasswd -f > /home/vagrant/.vnc/passwd"
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
echo "🔧 Configuring Firefox..."
# Create phishing email HTML
mkdir -p /home/vagrant/PhishingEmailDemo

cat <<EOF > /home/vagrant/PhishingEmailDemo/inbox.html
<!DOCTYPE html>
<html>
<head><title>Inbox</title></head>
<body>
  <h2>Inbox</h2>
  <hr>
  <p><strong>From:</strong> admin@fakebank.com</p>
  <p><strong>Subject:</strong> Urgent: Invoice Due</p>
  <p>
    Dear user,<br><br>
    Please review the attached invoice.<br>
    <a href="http://192.168.56.10/malicious_page.html" target="_blank">Click here to view invoice</a><br><br>
    Regards,<br>
    Accounts Team
  </p>
</body>
</html>
EOF

# Make vagrant user own it
chown -R vagrant:vagrant /home/vagrant/PhishingEmailDemo

# Add Firefox to autostart with inbox.html (optional)
mkdir -p /home/vagrant/.config/autostart

cat <<EOF > /home/vagrant/.config/autostart/inbox.desktop
[Desktop Entry]
Type=Application
Exec=firefox /home/vagrant/PhishingEmailDemo/inbox.html
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Inbox Email
EOF

chown -R vagrant:vagrant /home/vagrant/.config/autostart

echo "✅ Setup complete!"
echo "👉 Access the VM GUI at: http://192.168.1.6:6080/vnc.html"
echo "🔐 VNC Password: vagrant"
#!/bin/bash
set -e

echo "=== 🌀 Updating system packages ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== 🐳 Installing Docker & Docker Compose ==="
sudo apt-get install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

echo "=== 📁 Creating Guacamole directory ==="
mkdir -p ~/guacamole
cd ~/guacamole

echo "=== 📝 Creating docker-compose.yml ==="
cat <<EOF > docker-compose.yml
version: '3'
services:
  guacd:
    image: guacamole/guacd
    container_name: guacd
    restart: always

  guacamole:
    image: guacamole/guacamole
    container_name: guacamole
    restart: always
    ports:
      - "8080:8080"
    links:
      - guacd
      - mysql
    environment:
      MYSQL_HOSTNAME: mysql
      MYSQL_PORT: 3306
      MYSQL_DATABASE: guacamole_db
      MYSQL_USER: guacamole_user
      MYSQL_PASSWORD: guac_pass
      MYSQL_ROOT_PASSWORD: root_pass

  mysql:
    image: mysql:8.0
    container_name: mysql
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: root_pass
      MYSQL_DATABASE: guacamole_db
      MYSQL_USER: guacamole_user
      MYSQL_PASSWORD: guac_pass
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
EOF

echo "=== 🚀 Starting Guacamole stack ==="
sudo docker-compose up -d

echo "=== ⏳ Waiting for MySQL to be ready ==="
sleep 20

echo "=== 📜 Initializing Guacamole database ==="
sudo docker run --rm guacamole/guacamole /opt/guacamole/bin/initdb.sh --mysql > initdb.sql
sudo docker exec -i mysql mysql -uguacamole_user -pguac_pass guacamole_db < initdb.sql

echo "=== ✅ Guacamole setup complete! ==="
echo "🌐 Access it at: http://<your-server-ip>:8080/guacamole"
echo "🔑 Default login: guacadmin / guacadmin"
echo "⚠️ Change password immediately after login."

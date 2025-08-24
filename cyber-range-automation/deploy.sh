#!/bin/bash
# Deployment script for Cyber Range UI + Backend

set -e  # Exit on error

FRONTEND_DIR="/home/cyberrange/Cyberrange/cyber-range-automation/frontend/cyber-range-ui"
DEPLOY_DIR="/var/www/html/browser"

echo "==> Changing to frontend directory..."
cd $FRONTEND_DIR

echo "==> Building Angular app for production..."
ng build --configuration production

echo "==> Removing old frontend files..."
sudo rm -rf ${DEPLOY_DIR}/*

echo "==> Copying new frontend build..."
sudo cp -r dist/cyber-range-ui/browser/* ${DEPLOY_DIR}/

echo "==> Checking if index.html exists..."
if [ -f "${DEPLOY_DIR}/index.html" ]; then
    echo "index.html found ✅"
else
    echo "index.html missing ❌"
    exit 1
fi

echo "==> Setting ownership and permissions..."
sudo chown -R www-data:www-data ${DEPLOY_DIR}
sudo chmod -R 755 ${DEPLOY_DIR}

echo "==> Restarting Nginx..."
sudo systemctl restart nginx

echo "==> Restarting backend service..."
sudo systemctl restart cyberrange-backend

echo "✅ Deployment completed successfully!"
exit 0
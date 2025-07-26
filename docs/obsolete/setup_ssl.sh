#!/bin/bash
# SSL Certificate Setup Script
# Run this script to set up SSL certificates for your domain

set -e

DOMAIN="your-domain.com"
EMAIL="your-email@example.com"

echo "Setting up SSL certificates for $DOMAIN..."

# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
fi

# Stop nginx temporarily
sudo systemctl stop nginx

# Obtain SSL certificate
sudo certbot certonly --standalone \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# Configure auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Test renewal
sudo certbot renew --dry-run

echo "SSL certificates installed successfully!"
echo "Certificates are located at: /etc/letsencrypt/live/$DOMAIN/"
echo "Don't forget to update your nginx configuration with the correct domain name!"

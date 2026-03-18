#!/bin/bash

# Generate self-signed SSL certificates for development
# This script creates certificates for localhost and matchgorithm.com domains

set -e

CERT_DIR="./certs"
DOMAIN="matchgorithm.com"
SUBDOMAINS=("directus.$DOMAIN" "api.$DOMAIN" "app.$DOMAIN")

echo "Generating self-signed SSL certificates for development..."

# Create certificate directory if it doesn't exist
mkdir -p "$CERT_DIR"

# Generate private key
openssl genrsa -out "$CERT_DIR/privkey.pem" 2048

# Generate certificate signing request
cat > "$CERT_DIR/cert.conf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = Organization
OU = Unit
CN = $DOMAIN

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = *.$DOMAIN
DNS.3 = localhost
IP.1 = 127.0.0.1
EOF

# Generate self-signed certificate
openssl req -new -x509 -key "$CERT_DIR/privkey.pem" -out "$CERT_DIR/fullchain.pem" -days 365 -config "$CERT_DIR/cert.conf" -extensions v3_req

# Create symbolic links for Directus
mkdir -p "$CERT_DIR/live/directus.$DOMAIN"
ln -sf "../../fullchain.pem" "$CERT_DIR/live/directus.$DOMAIN/fullchain.pem"
ln -sf "../../privkey.pem" "$CERT_DIR/live/directus.$DOMAIN/privkey.pem"

echo "SSL certificates generated successfully!"
echo "Certificate files:"
echo "  - $CERT_DIR/fullchain.pem (certificate chain)"
echo "  - $CERT_DIR/privkey.pem (private key)"
echo ""
echo "For production, replace these with Let's Encrypt certificates."
#!/bin/bash
# =============================================================================
# Server Hardening Script
# UFW + Fail2Ban Configuration
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# UFW Configuration
# =============================================================================
configure_ufw() {
    log_info "Configuring UFW (Uncomplicated Firewall)..."

    # Reset UFW to defaults
    log_info "Resetting UFW to defaults..."
    ufw --force reset

    # Set default policies
    log_info "Setting default policies: deny incoming, allow outgoing"
    ufw default deny incoming
    ufw default allow outgoing

    # Allow SSH (critical - don't lock yourself out!)
    log_info "Allowing SSH on port 22..."
    ufw allow 22/tcp comment 'SSH'

    # Allow HTTP and HTTPS
    log_info "Allowing HTTP (80) and HTTPS (443)..."
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'

    # Allow Podman/Docker networks (internal)
    log_info "Allowing internal container networks..."
    ufw allow from 172.16.0.0/12 comment 'Podman/Docker networks'
    ufw allow from 10.0.0.0/8 comment 'Private networks'
    ufw allow from 192.168.0.0/16 comment 'Private networks'

    # Rate limit SSH to prevent brute force
    log_info "Enabling SSH rate limiting..."
    ufw limit 22/tcp comment 'SSH rate limit'

    # Enable UFW
    log_info "Enabling UFW..."
    ufw --force enable

    # Show status
    log_info "UFW status:"
    ufw status verbose
}

# =============================================================================
# Fail2Ban Configuration
# =============================================================================
configure_fail2ban() {
    log_info "Configuring Fail2Ban..."

    # Create Fail2Ban configuration directory
    mkdir -p /etc/fail2ban/jail.d
    mkdir -p /etc/fail2ban/filter.d

    # Main jail configuration
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
# Ban time: 1 hour (3600 seconds)
bantime = 3600

# Find time: 10 minutes
findtime = 600

# Max retries: 5
maxretry = 5

# Backend: systemd
backend = systemd

# Email notifications (optional)
# destemail = admin@example.com
# sender = fail2ban@example.com
# mta = sendmail

# Action: ban only (change to %(action_mwl)s for email notifications)
action = %(action_)s

# =============================================================================
# Jails
# =============================================================================

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 5

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10

[nginx-botsearch]
enabled = true
filter = nginx-botsearch
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 5

[nginx-badbots]
enabled = true
filter = nginx-badbots
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 3

[ai-agent-api]
enabled = true
filter = ai-agent-api
port = 8000
logpath = /opt/ai-agent/logs/api.log
maxretry = 10
findtime = 300
bantime = 1800
EOF

    # Create custom filter for AI Agent API
    cat > /etc/fail2ban/filter.d/ai-agent-api.conf << 'EOF'
[Definition]
failregex = ^.*"<HOST>".*"(POST|GET).*/api/.*" (401|403|429).*$`
            ^.*"<HOST>".*"POST.*/agent".*(401|403).*$`
ignoreregex = ^.*"<HOST>".*"/health".*$
EOF

    # Create Nginx filters if they don't exist
    if [ ! -f /etc/fail2ban/filter.d/nginx-limit-req.conf ]; then
        cat > /etc/fail2ban/filter.d/nginx-limit-req.conf << 'EOF'
[Definition]
failregex = limiting requests, excess:.* by zone "[^"]+".* client: <HOST>
EOF
    fi

    if [ ! -f /etc/fail2ban/filter.d/nginx-botsearch.conf ]; then
        cat > /etc/fail2ban/filter.d/nginx-botsearch.conf << 'EOF'
[Definition]
failregex = ^<HOST> .* "(GET|POST|HEAD).*\.(php|asp|aspx|jsp|cgi|pl|py|rb).* HTTP/[0-9.]+" 404
EOF
    fi

    # Restart Fail2Ban
    log_info "Restarting Fail2Ban..."
    systemctl restart fail2ban
    systemctl enable fail2ban

    # Show status
    log_info "Fail2Ban status:"
    fail2ban-client status
}

# =============================================================================
# Kernel Hardening (sysctl)
# =============================================================================
configure_sysctl() {
    log_info "Configuring kernel parameters..."

    cat > /etc/sysctl.d/99-ai-agent-hardening.conf << 'EOF'
# =============================================================================
# Network Security
# =============================================================================

# Disable IP source routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Disable ICMP redirect acceptance
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# Disable ICMP secure redirect acceptance
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0

# Ignore ICMP echo requests (ping)
net.ipv4.icmp_echo_ignore_all = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Ignore bogus ICMP responses
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Enable SYN flood protection
net.ipv4.tcp_syncookies = 1

# Disable IPv6 if not needed (optional)
# net.ipv6.conf.all.disable_ipv6 = 1
# net.ipv6.conf.default.disable_ipv6 = 1

# =============================================================================
# Connection Tracking
# =============================================================================

# Increase connection tracking table size
net.netfilter.nf_conntrack_max = 65536

# Reduce connection tracking timeout
net.netfilter.nf_conntrack_tcp_timeout_established = 600

# =============================================================================
# Process Security
# =============================================================================

# Enable ASLR
kernel.randomize_va_space = 2

# Restrict ptrace
kernel.yama.ptrace_scope = 1

# Increase PID max
kernel.pid_max = 65536
EOF

    # Apply sysctl settings
    sysctl --system
}

# =============================================================================
# SSH Hardening
# =============================================================================
configure_ssh() {
    log_info "Configuring SSH hardening..."

    # Backup original config
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d)

    # Apply hardening settings
    cat >> /etc/ssh/sshd_config << 'EOF'

# =============================================================================
# SSH Hardening
# =============================================================================

# Disable root login
PermitRootLogin no

# Disable password authentication (use keys only)
PasswordAuthentication no
PubkeyAuthentication yes

# Limit authentication attempts
MaxAuthTries 3

# Set idle timeout
ClientAliveInterval 300
ClientAliveCountMax 2

# Disable X11 forwarding
X11Forwarding no

# Limit users (optional - uncomment and modify)
# AllowUsers deploy admin

# Use only strong algorithms
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com
KexAlgorithms curve25519-sha256@libssh.org,ecdh-sha2-nistp521,ecdh-sha2-nistp384,ecdh-sha2-nistp256,diffie-hellman-group-exchange-sha256

# Disable unused features
AllowTcpForwarding no
PermitTunnel no
EOF

    # Restart SSH
    systemctl restart sshd

    log_warn "SSH configuration updated. Make sure you have key-based access before disconnecting!"
}

# =============================================================================
# Podman Security
# =============================================================================
configure_podman_security() {
    log_info "Configuring Podman security..."

    # Enable user namespaces
    echo "user.max_user_namespaces=28633" > /etc/sysctl.d/99-userns.conf
    sysctl --system

    # Configure rootless Podman (if needed)
    log_info "Rootless Podman configuration:"
    log_info "Run 'podman system migrate' as each user to apply changes"
}

# =============================================================================
# Main
# =============================================================================
main() {
    log_info "Starting server hardening..."

    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root (use sudo)"
        exit 1
    fi

    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log_info "Detected OS: $NAME $VERSION_ID"
    fi

    # Install required packages
    log_info "Installing required packages..."
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y ufw fail2ban
    elif command -v yum &> /dev/null; then
        yum install -y ufw fail2ban
    elif command -v dnf &> /dev/null; then
        dnf install -y ufw fail2ban
    else
        log_error "Unsupported package manager"
        exit 1
    fi

    # Run configurations
    configure_sysctl
    configure_ufw
    configure_fail2ban
    configure_ssh
    configure_podman_security

    log_info "Server hardening completed!"
    log_info ""
    log_info "Summary:"
    log_info "  - UFW: Enabled with default deny"
    log_info "  - Fail2Ban: Configured for SSH, Nginx, and API"
    log_info "  - Kernel: Security parameters applied"
    log_info "  - SSH: Hardened configuration"
    log_info ""
    log_warn "Please verify SSH access before closing this session!"
    log_warn "If locked out, use console access to restore /etc/ssh/sshd_config.bak.*"
}

# Run main function
main "$@"

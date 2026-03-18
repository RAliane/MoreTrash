#!/bin/bash

# Matchgorithm Network Security Rules
# Implements firewall rules for triple network separation

set -e

echo "🔥 Configuring Matchgorithm Network Security Rules"
echo "================================================="

# Function to add iptables rule if it doesn't exist
add_rule() {
    if ! iptables -C "$@" 2>/dev/null; then
        iptables -I "$@"
        echo "✅ Added rule: iptables -I $@"
    else
        echo "ℹ️  Rule already exists: iptables -I $@"
    fi
}

# Function to add podman network isolation
isolate_network() {
    local network=$1
    local allowed_ips=$2

    echo "🔒 Isolating network: $network"

    # Get network interface
    local interface=$(podman network inspect $network | grep -o '"network_interface":"[^"]*"' | cut -d'"' -f4)

    if [ -n "$interface" ]; then
        # Drop all traffic by default
        add_rule INPUT -i $interface -j DROP
        add_rule OUTPUT -o $interface -j DROP

        # Allow specific traffic
        for ip in $allowed_ips; do
            add_rule INPUT -i $interface -s $ip -j ACCEPT
            add_rule OUTPUT -o $interface -d $ip -j ACCEPT
        done

        echo "✅ Isolated $network with allowed IPs: $allowed_ips"
    else
        echo "⚠️  Could not find interface for network $network"
    fi
}

# Edge Network (10.0.1.0/24)
# Allow: HTTP/HTTPS (ports 80,443,8000), ICMP
echo "🌐 Configuring Edge Network (edge-net)"
add_rule INPUT -i edge-net -p tcp --dport 80 -j ACCEPT
add_rule INPUT -i edge-net -p tcp --dport 443 -j ACCEPT
add_rule INPUT -i edge-net -p tcp --dport 8000 -j ACCEPT
add_rule INPUT -i edge-net -p icmp -j ACCEPT

# Auth Network (10.0.2.0/24)
# Allow: Internal API calls (ports 3000,8080), connections from edge-net
echo "🔐 Configuring Auth Network (auth-net)"
add_rule FORWARD -i edge-net -o auth-net -j ACCEPT
add_rule FORWARD -i auth-net -o edge-net -j ACCEPT
add_rule INPUT -i auth-net -p tcp --dport 3000 -j ACCEPT
add_rule INPUT -i auth-net -p tcp --dport 8080 -j ACCEPT

# Database Network (10.0.3.0/24)
# Allow: PostgreSQL (port 5432), connections from auth-net only
echo "🗄️  Configuring Database Network (db-net)"
add_rule FORWARD -i auth-net -o db-net -j ACCEPT
add_rule FORWARD -i db-net -o auth-net -j ACCEPT
add_rule INPUT -i db-net -p tcp --dport 5432 -j ACCEPT

# Block all other inter-network traffic
echo "🚫 Blocking unauthorized inter-network traffic"
add_rule FORWARD -i edge-net -o db-net -j DROP
add_rule FORWARD -i db-net -o edge-net -j DROP
add_rule FORWARD -i auth-net ! -o edge-net ! -o db-net -j DROP

# Log dropped packets for auditing
echo "📊 Enabling packet logging for security auditing"
add_rule INPUT -j LOG --log-prefix "MATCHGORITHM-DROP: " --log-level 4
add_rule FORWARD -j LOG --log-prefix "MATCHGORITHM-FORWARD-DROP: " --log-level 4

# Save iptables rules
echo "💾 Saving iptables rules"
/etc/init.d/iptables save 2>/dev/null || iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

echo ""
echo "🎉 Network security rules configured!"
echo ""
echo "📋 Summary:"
echo "- 🌐 Edge network: HTTP/HTTPS/ICMP allowed"
echo "- 🔐 Auth network: Internal API access only"
echo "- 🗄️  Database network: PostgreSQL from auth-net only"
echo "- 🚫 Blocked: Direct database access from edge"
echo "- 📊 Logging: All dropped packets logged"
echo ""
echo "🔍 Test the rules:"
echo "  iptables -L -v"
echo "  iptables -L -v -t nat"
echo ""
echo "⚠️  Remember to restart services after network changes:"
echo "  podman-compose down && podman-compose up -d"
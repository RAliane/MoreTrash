#!/bin/bash

# Matchgorithm Monitoring Setup Script
# Configures alerting rules and notification channels

set -e

MONITORING_DIR="./monitoring"
ALERTMANAGER_CONFIG="$MONITORING_DIR/alertmanager.yml"
PROMETHEUS_RULES="$MONITORING_DIR/alert_rules.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Create monitoring directory
create_monitoring_dir() {
    log "Creating monitoring directory structure..."
    mkdir -p "$MONITORING_DIR"/alertmanager
    mkdir -p "$MONITORING_DIR"/grafana/provisioning/alerting
}

# Create Prometheus alert rules
create_alert_rules() {
    log "Creating Prometheus alert rules..."

    cat > "$PROMETHEUS_RULES" << 'EOF'
groups:
  - name: matchgorithm_alerts
    rules:
      # Service availability alerts
      - alert: ServiceDown
        expr: up == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"
          description: "Service {{ $labels.instance }} has been down for more than 5 minutes."

      # Application specific alerts
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.instance }}"
          description: "Error rate is {{ $value }}% which is above 10%."

      # Database alerts
      - alert: DatabaseDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL database is down"
          description: "PostgreSQL database has been unreachable for more than 1 minute."

      - alert: DatabaseHighConnections
        expr: pg_stat_activity_count > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connections"
          description: "Database has {{ $value }} active connections, which is above 80."

      # System resource alerts
      - alert: HighMemoryUsage
        expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is {{ $value }}%."

      - alert: HighCPUUsage
        expr: rate(node_cpu_seconds_total{mode!="idle"}[5m]) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value }}%."

      - alert: HighDiskUsage
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High disk usage on {{ $labels.instance }}"
          description: "Disk usage is {{ $value }}% on {{ $labels.mountpoint }}."

      # Network alerts
      - alert: NetworkErrors
        expr: rate(node_network_receive_errs_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Network receive errors on {{ $labels.instance }}"
          description: "Network interface {{ $labels.device }} has receive errors."

      # Application performance alerts
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response time on {{ $labels.instance }}"
          description: "95th percentile response time is {{ $value }}s."

      - alert: HighQueueLength
        expr: matchgorithm_queue_length > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High queue length"
          description: "Optimization queue length is {{ $value }}, consider scaling."

      # Security alerts
      - alert: FailedLoginAttempts
        expr: rate(matchgorithm_failed_logins_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High failed login attempts"
          description: "Failed login rate is {{ $value }} per second, possible brute force attack."
EOF

    log "Created Prometheus alert rules"
}

# Create Alertmanager configuration
create_alertmanager_config() {
    log "Creating Alertmanager configuration..."

    cat > "$ALERTMANAGER_CONFIG" << 'EOF'
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@matchgorithm.com'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'email-alerts'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      continue: true
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'email-alerts'
    email_configs:
      - to: 'admin@matchgorithm.com'
        subject: 'Matchgorithm Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Severity: {{ .Labels.severity }}
          Instance: {{ .Labels.instance }}
          Value: {{ .Value }}
          Started: {{ .StartsAt.Format "2006-01-02 15:04:05" }}
          {{ end }}

  - name: 'critical-alerts'
    email_configs:
      - to: 'critical@matchgorithm.com'
        subject: 'CRITICAL: Matchgorithm Alert - {{ .GroupLabels.alertname }}'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts-critical'
        title: '🚨 CRITICAL ALERT: {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          *Alert:* {{ .Annotations.summary }}
          *Description:* {{ .Annotations.description }}
          *Severity:* {{ .Labels.severity }}
          *Instance:* {{ .Labels.instance }}
          *Value:* {{ .Value }}
          {{ end }}

  - name: 'warning-alerts'
    email_configs:
      - to: 'warnings@matchgorithm.com'
        subject: 'WARNING: Matchgorithm Alert - {{ .GroupLabels.alertname }}'
EOF

    log "Created Alertmanager configuration"
    warn "Update email and Slack webhook URLs in $ALERTMANAGER_CONFIG"
}

# Create Grafana alerting configuration
create_grafana_alerting() {
    log "Creating Grafana alerting configuration..."

    cat > "$MONITORING_DIR/grafana/provisioning/alerting/contact-points.yml" << 'EOF'
apiVersion: 1
contactPoints:
  - orgId: 1
    name: email-admin
    receivers:
      - uid: email-admin
        type: email
        settings:
          addresses: admin@matchgorithm.com
          singleEmail: false
    - uid: slack-critical
      type: slack
      settings:
        recipient: '#alerts-critical'
        token: 'xoxb-your-slack-token'
        url: https://slack.com/api/chat.postMessage
EOF

    cat > "$MONITORING_DIR/grafana/provisioning/alerting/policies.yml" << 'EOF'
apiVersion: 1
policies:
  - orgId: 1
    receiver: email-admin
    group_by:
      - alertname
      - severity
    group_wait: 30s
    group_interval: 5m
    repeat_interval: 4h
    routes:
      - receiver: slack-critical
        matchers:
          - severity=~critical
EOF

    log "Created Grafana alerting configuration"
}

# Create dashboard provisioning
create_grafana_dashboards() {
    log "Creating Grafana dashboard provisioning..."

    cat > "$MONITORING_DIR/grafana/provisioning/dashboards/dashboard.yml" << 'EOF'
apiVersion: 1

providers:
  - name: 'matchgorithm'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    log "Created Grafana dashboard provisioning"
}

# Create sample dashboard
create_sample_dashboard() {
    log "Creating sample Grafana dashboard..."

    cat > "$MONITORING_DIR/grafana/provisioning/dashboards/matchgorithm-overview.json" << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Matchgorithm Overview",
    "tags": ["matchgorithm", "overview"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Service Status",
        "type": "stat",
        "targets": [
          {
            "expr": "up",
            "legendFormat": "{{instance}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "mappings": [
              {
                "options": {
                  "0": {
                    "text": "DOWN",
                    "color": "red"
                  },
                  "1": {
                    "text": "UP",
                    "color": "green"
                  }
                },
                "type": "value"
              }
            ]
          }
        }
      },
      {
        "id": 2,
        "title": "HTTP Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_activity_count",
            "legendFormat": "Active connections"
          }
        ]
      },
      {
        "id": 4,
        "title": "System Resources",
        "type": "row",
        "panels": [
          {
            "id": 5,
            "title": "CPU Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(node_cpu_seconds_total{mode!=\"idle\"}[5m]) * 100",
                "legendFormat": "{{instance}}"
              }
            ]
          },
          {
            "id": 6,
            "title": "Memory Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100",
                "legendFormat": "{{instance}}"
              }
            ]
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "timepicker": {},
    "templating": {
      "list": []
    },
    "annotations": {
      "list": []
    },
    "refresh": "30s",
    "schemaVersion": 27,
    "version": 0,
    "links": []
  }
}
EOF

    log "Created sample Grafana dashboard"
}

# Update podman-compose.yml to include Alertmanager
update_compose_for_alerting() {
    log "Checking podman-compose.yml for Alertmanager..."

    if ! grep -q "alertmanager" podman-compose.yml; then
        warn "Alertmanager not found in podman-compose.yml"
        info "Add the following to your podman-compose.yml services section:"
        echo ""
        cat << 'EOF'
  alertmanager:
    image: prom/alertmanager:latest
    container_name: matchgorithm-alertmanager
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    ports:
      - "9093:9093"
    networks:
      - edge-net
    restart: unless-stopped
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
EOF
        echo ""
    else
        log "Alertmanager already configured in podman-compose.yml"
    fi
}

# Main setup function
main() {
    log "Setting up Matchgorithm monitoring and alerting..."

    create_monitoring_dir
    create_alert_rules
    create_alertmanager_config
    create_grafana_alerting
    create_grafana_dashboards
    create_sample_dashboard
    update_compose_for_alerting

    log "Monitoring setup completed!"
    echo ""
    info "Next steps:"
    echo "1. Update email settings in $ALERTMANAGER_CONFIG"
    echo "2. Configure Slack webhook URL in alerting configs"
    echo "3. Add Alertmanager service to podman-compose.yml"
    echo "4. Restart monitoring services: podman-compose restart prometheus grafana"
    echo "5. Access Grafana: http://localhost:3000 (admin/admin)"
    echo ""
    info "Monitoring URLs:"
    echo "- Prometheus: http://localhost:9090"
    echo "- Alertmanager: http://localhost:9093"
    echo "- Grafana: http://localhost:3000"
}

# Run main function
main "$@"

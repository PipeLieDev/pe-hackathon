# Incident Response Alert Documentation

This document details the alerting system for the MLH PE Hackathon Flask application, including all configured alerts, their trigger conditions, and notification configurations.

## Overview

The monitoring stack consists of:
- **Prometheus**: Metrics collection and alerting engine
- **Alertmanager**: Alert routing and notification management
- **Node Exporter**: System-level metrics collection
- **Discord**: Notification destination for alerts

## Alert Rules Configuration

### 1. ServiceDown Alert

**Purpose**: Detects when Flask application instances are unavailable.

**Configuration** (`alert_rules.yml`):
```yaml
- alert: ServiceDown
  expr: up == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Flask app is down"
    description: "Flask app has been down for more than 1 minute."
```

**Trigger Conditions**:
- Metric: `up` (Prometheus built-in metric indicating if a target is reachable)
- Condition: `up == 0` (target is unreachable)
- Duration: Alert fires after 1 minute of continuous failure
- Severity: Critical

**What it monitors**:
- Flask app instances at `app1:5000` and `app2:5000`
- Uses Prometheus `up` metric which returns 1 if target responds, 0 if unreachable

**Example Scenario**:
- Container crashes or becomes unresponsive
- Network connectivity issues
- Application hangs or exits unexpectedly

### 2. HighErrorRate Alert

**Purpose**: Detects elevated HTTP error rates indicating application issues.

**Configuration** (`alert_rules.yml`):
```yaml
- alert: HighErrorRate
  expr: rate(flask_http_request_total{status=~"5.."}[5m]) / rate(flask_http_request_total[5m]) > 0.05
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High error rate detected"
    description: "Error rate is {{ $value }}% over the last 5 minutes."
```

**Trigger Conditions**:
- Metric: `flask_http_request_total` (Flask/Prometheus client metric)
- Condition: Error rate > 5% (5xx status codes / total requests)
- Time window: 5-minute rolling average
- Duration: Alert fires after 2 minutes of high error rate
- Severity: Warning

**What it monitors**:
- HTTP 5xx server error responses
- Calculated as: `(rate of 5xx responses) / (rate of all responses) > 0.2`

**Example Scenario**:
- Database connection failures
- Application bugs causing 500 errors
- Resource exhaustion (memory, CPU)
- External service dependencies failing

### 3. HighLatency Alert

**Purpose**: Detects slow response times affecting user experience.

**Configuration** (`alert_rules.yml`):
```yaml
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(flask_http_request_duration_seconds_bucket[5m])) > 2
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High request latency"
    description: "95th percentile latency is {{ $value }}s."
```

**Trigger Conditions**:
- Metric: `flask_http_request_duration_seconds_bucket` (Flask histogram metric)
- Condition: 95th percentile response time > 2 seconds
- Time window: 5-minute rolling calculation
- Duration: Alert fires after 2 minutes of high latency
- Severity: Warning

**What it monitors**:
- HTTP request response times
- 95th percentile (worst 5% of requests)
- Measures end-to-end request processing time

**Example Scenario**:
- Slow database queries
- Inefficient application code
- Resource contention
- Network latency issues

### 4. HighCPUUsage Alert

**Purpose**: Detects high CPU utilization on the host system.

**Configuration** (`alert_rules.yml`):
```yaml
- alert: HighCPUUsage
  expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High CPU usage detected"
    description: "CPU usage is {{ $value }}% over the last 5 minutes."
```

**Trigger Conditions**:
- Metric: `node_cpu_seconds_total` (Node Exporter metric)
- Condition: CPU usage > 90%
- Calculation: `100 - (idle CPU percentage)`
- Time window: 5-minute rolling average
- Duration: Alert fires after 2 minutes of high CPU
- Severity: Warning

**What it monitors**:
- Host system CPU utilization
- All CPU cores averaged together
- Measures actual CPU usage (not idle time)

**Example Scenario**:
- Application performance issues causing high CPU
- Resource-intensive background tasks
- Memory pressure causing CPU-intensive garbage collection
- System-level CPU bottlenecks

## Alert Routing Configuration

### Alertmanager Routing Rules

**Configuration** (`alertmanager.yml`):
```yaml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'discord'
  routes:
  - match:
      severity: critical
    receiver: 'discord-critical'
```

**Routing Logic**:
- **Default receiver**: `discord` (for warning alerts)
- **Critical alerts**: Route to `discord-critical` receiver
- **Grouping**: Alerts grouped by `alertname` to avoid spam
- **Timing**:
  - `group_wait`: 10s (wait for similar alerts before sending)
  - `group_interval`: 10s (interval between grouped notifications)
  - `repeat_interval`: 1h (resend resolved alerts every hour)

## Notification Configuration

### Discord Webhook Receivers

#### Regular Alerts (Warning Severity)
```yaml
- name: 'discord'
  discord_configs:
  - webhook_url: 'https://discord.com/api/webhooks/[WEBHOOK_ID]/[WEBHOOK_TOKEN]'
    send_resolved: true
    content: |
      {{ range .Alerts }}**{{ .Labels.alertname }}**
      {{ .Annotations.summary }}
      {{ .Annotations.description }}
      {{ end }}
```

#### Critical Alerts
```yaml
- name: 'discord-critical'
  discord_configs:
  - webhook_url: 'https://discord.com/api/webhooks/[WEBHOOK_ID]/[WEBHOOK_TOKEN]'
    send_resolved: true
    content: |
      {{ range .Alerts }}**{{ .Labels.alertname }}**
      {{ .Annotations.summary }}
      {{ .Annotations.description }}
      {{ end }}
```

**Notification Format**:
- **Critical alerts**: Marked with 🚨 emoji prefix (handled by template)
- **Warning alerts**: Standard formatting
- **Content includes**:
  - Alert name
  - Summary annotation
  - Description annotation
- **Resolved notifications**: Sent when alerts are resolved

## Metrics Collection Configuration

### Prometheus Scrape Targets

**Configuration** (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'flask_app'
    static_configs:
      - targets: ['app1:5000', 'app2:5000']

  - job_name: 'node'
    static_configs:
      - targets: ['node_exporter:9100']
```

**Targets**:
- **Flask apps**: `app1:5000`, `app2:5000` (load-balanced application instances)
- **Node Exporter**: `node_exporter:9100` (system metrics)

## Alert Lifecycle

### 1. Alert Generation
- Prometheus evaluates alert rules every 15 seconds
- When conditions are met for the specified duration, alert becomes `firing`

### 2. Alert Routing
- Alertmanager receives firing alerts from Prometheus
- Applies routing rules based on labels (severity, etc.)
- Groups similar alerts to reduce noise

### 3. Notification
- Alertmanager sends notifications to configured receivers
- Discord webhooks receive formatted messages
- Notifications include alert details and contextual information

### 4. Resolution
- When alert conditions are no longer met, alert becomes `resolved`
- Alertmanager sends resolution notifications
- Resolved alerts are suppressed for `repeat_interval` duration

## Testing Alerts

### ServiceDown Alert Test
```bash
# Stop an app instance
docker stop pe-hackathon-app1-1

# Wait 1 minute for alert to fire
# Check Prometheus: http://localhost:9090
# Check Alertmanager: http://localhost:9093
# Observe Discord notifications
```

### High CPU Alert Test
```bash
# Generate CPU load
stress --cpu 4 --timeout 300

# Wait 2 minutes for alert to fire
# Monitor via Grafana/Node Exporter metrics
```

## Troubleshooting

### Common Issues

1. **Alerts not firing**: Check Prometheus targets are reachable
2. **Discord notifications not received**: Verify webhook URL is valid
3. **False positives**: Adjust alert thresholds based on baseline metrics
4. **Alert spam**: Review grouping and repeat interval settings

### Useful Queries

```promql
# Check service health
up{job="flask_app"}

# Monitor error rates
rate(flask_http_request_total{status=~"5.."}[5m]) / rate(flask_http_request_total[5m])

# Check latency
histogram_quantile(0.95, rate(flask_http_request_duration_seconds_bucket[5m]))

# Monitor CPU usage
100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

## Maintenance

- **Review alert thresholds** quarterly based on application performance
- **Test alert notifications** monthly to ensure Discord webhooks are functional
- **Update contact information** when team members change
- **Document alert responses** in incident response procedures
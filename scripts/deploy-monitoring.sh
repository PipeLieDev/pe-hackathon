#!/usr/bin/env bash
set -euo pipefail

MONITORING_NS="monitoring"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Deploying Monitoring Stack to K3s ==="
echo ""

# --- Namespace ---
echo "--- Creating monitoring namespace ---"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/namespace.yaml"

# --- Prometheus ---
echo "--- Deploying Prometheus ---"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/prometheus-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/alert-rules-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/prometheus-deployment.yaml"
kubectl rollout status deployment/prometheus -n "${MONITORING_NS}" --timeout=120s

# --- Alertmanager ---
echo "--- Deploying Alertmanager ---"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/alertmanager-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/alertmanager-deployment.yaml"
kubectl rollout status deployment/alertmanager -n "${MONITORING_NS}" --timeout=120s

# --- Loki ---
echo "--- Deploying Loki ---"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/loki-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/loki-deployment.yaml"
kubectl rollout status deployment/loki -n "${MONITORING_NS}" --timeout=120s

# --- Promtail ---
echo "--- Deploying Promtail ---"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/promtail-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/promtail-daemonset.yaml"
kubectl rollout status daemonset/promtail -n "${MONITORING_NS}" --timeout=120s

# --- Grafana ---
echo "--- Deploying Grafana ---"

# Create dashboard ConfigMap from JSON file
DASHBOARD_FILE="${SCRIPT_DIR}/docs/IncidentReportQuest/grafanaDashboard.json"
if [ -f "${DASHBOARD_FILE}" ]; then
  kubectl create configmap grafana-dashboards \
    --from-file=url-shortener.json="${DASHBOARD_FILE}" \
    -n "${MONITORING_NS}" --dry-run=client -o yaml | kubectl apply -f -
else
  echo "WARN: ${DASHBOARD_FILE} not found — skipping dashboard ConfigMap"
fi

kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/grafana-deployment.yaml"
kubectl rollout status deployment/grafana -n "${MONITORING_NS}" --timeout=120s

# --- Status ---
echo ""
echo "=== Monitoring Stack Deployed ==="
echo ""
echo "Pod status:"
kubectl get pods -n "${MONITORING_NS}" -o wide
echo ""
echo "Services:"
kubectl get svc -n "${MONITORING_NS}"
echo ""
echo "Access points:"
echo "  Grafana:    http://<node-ip>:30030  (admin/admin)"
echo "  Prometheus: http://<node-ip>:30090"

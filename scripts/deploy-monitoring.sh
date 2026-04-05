#!/usr/bin/env bash
set -euo pipefail

MONITORING_NS="monitoring"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Deploying Monitoring Stack to K3s ==="
echo ""

# --- Namespace ---
echo "--- Creating monitoring namespace ---"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/namespace.yaml"

# --- ConfigMaps from monitoring/ source files ---
echo "--- Creating ConfigMaps from monitoring configs ---"
kubectl create configmap prometheus-config \
  --from-file=prometheus.yml="${SCRIPT_DIR}/monitoring/prometheus.k8s.yml" \
  -n "${MONITORING_NS}" --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap alert-rules \
  --from-file=alert_rules.yml="${SCRIPT_DIR}/monitoring/alert_rules.yml" \
  -n "${MONITORING_NS}" --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap alertmanager-config \
  --from-file=config.yml="${SCRIPT_DIR}/monitoring/alertmanager.yml" \
  -n "${MONITORING_NS}" --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap loki-config \
  --from-file=local-config.yaml="${SCRIPT_DIR}/monitoring/loki.k8s.yml" \
  -n "${MONITORING_NS}" --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap promtail-config \
  --from-file=config.yml="${SCRIPT_DIR}/monitoring/promtail.k8s.yml" \
  -n "${MONITORING_NS}" --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap grafana-datasources \
  --from-file=datasources.yaml="${SCRIPT_DIR}/monitoring/grafana/provisioning/datasources/datasource.k8s.yml" \
  -n "${MONITORING_NS}" --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap grafana-dashboard-provider \
  --from-file=dashboards.yaml="${SCRIPT_DIR}/monitoring/grafana/provisioning/dashboards/provider.yml" \
  -n "${MONITORING_NS}" --dry-run=client -o yaml | kubectl apply -f -

# --- Apply workload manifests ---
echo "--- Applying workload manifests ---"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/prometheus-deployment.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/alertmanager-deployment.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/loki-deployment.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/promtail-daemonset.yaml"

# Create dashboard ConfigMap from JSON files
DASHBOARD_DIR="${SCRIPT_DIR}/monitoring/grafana/dashboards"
if ls "${DASHBOARD_DIR}"/*.json 1>/dev/null 2>&1; then
  kubectl create configmap grafana-dashboards \
    --from-file="${DASHBOARD_DIR}/" \
    -n "${MONITORING_NS}" --dry-run=client -o yaml | kubectl apply -f -
else
  echo "WARN: No dashboard JSON files found in ${DASHBOARD_DIR} — skipping dashboard ConfigMap"
fi

kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/grafana-deployment.yaml"

# --- Restart pods to pick up ConfigMap changes ---
echo "--- Restarting deployments to pick up config changes ---"
kubectl rollout restart deployment/prometheus -n "${MONITORING_NS}"
kubectl rollout restart deployment/alertmanager -n "${MONITORING_NS}"
kubectl rollout restart deployment/loki -n "${MONITORING_NS}"
kubectl rollout restart deployment/grafana -n "${MONITORING_NS}"
kubectl rollout restart daemonset/promtail -n "${MONITORING_NS}"

# --- Wait for rollouts ---
echo "--- Waiting for rollouts ---"
for deploy in prometheus alertmanager loki grafana; do
  kubectl rollout status deployment/${deploy} -n "${MONITORING_NS}" --timeout=120s
done
kubectl rollout status daemonset/promtail -n "${MONITORING_NS}" --timeout=120s

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

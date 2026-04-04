#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="url-shortener"
MONITORING_NS="monitoring"
IMAGE_TAG="${1:-latest}"
REPO="ghcr.io/cyanghxst/pe-hackathon"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Deploying URL Shortener to K3s ==="
echo "Image: ${REPO}:${IMAGE_TAG}"
echo ""

# --- Application namespace ---
echo "--- Applying application manifests ---"
kubectl apply -f "${SCRIPT_DIR}/k8s/namespace.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/configmap.yaml"

# Secrets (skip if not present — must be created manually)
if [ -f "${SCRIPT_DIR}/k8s/secrets.yaml" ]; then
  kubectl apply -f "${SCRIPT_DIR}/k8s/secrets.yaml"
else
  echo "WARN: k8s/secrets.yaml not found. Create it from k8s/secrets.yaml.example"
  echo "      See docs/k8s-setup.md Step 4"
fi

kubectl apply -f "${SCRIPT_DIR}/k8s/postgres-cluster.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/valkey-deployment.yaml"

echo "--- Waiting for PostgreSQL cluster to be ready ---"
kubectl wait cluster/postgres-cluster -n "${NAMESPACE}" \
  --for=condition=Ready --timeout=180s || echo "WARN: PostgreSQL cluster not ready yet — continuing"

kubectl apply -f "${SCRIPT_DIR}/k8s/app-deployment.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/app-service.yaml"

# Update image tag if specified
if [ "${IMAGE_TAG}" != "latest" ]; then
  echo "--- Setting image to ${REPO}:${IMAGE_TAG} ---"
  kubectl set image deployment/url-shortener \
    url-shortener="${REPO}:${IMAGE_TAG}" -n "${NAMESPACE}"
fi

echo "--- Waiting for app rollout ---"
kubectl rollout status deployment/url-shortener -n "${NAMESPACE}" --timeout=120s

# --- Monitoring namespace ---
echo ""
echo "--- Applying monitoring manifests ---"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/namespace.yaml"

# Prometheus
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/prometheus-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/alert-rules-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/prometheus-deployment.yaml"

# Alertmanager
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/alertmanager-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/alertmanager-deployment.yaml"

# Loki
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/loki-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/loki-deployment.yaml"

# Promtail
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/promtail-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/promtail-daemonset.yaml"

# Grafana dashboard from JSON file
kubectl create configmap grafana-dashboards \
  --from-file=url-shortener.json="${SCRIPT_DIR}/docs/IncidentReportQuest/grafanaDashboard.json" \
  -n "${MONITORING_NS}" --dry-run=client -o yaml | kubectl apply -f -

# Grafana
kubectl apply -f "${SCRIPT_DIR}/k8s/monitoring/grafana-deployment.yaml"

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Pod status:"
kubectl get pods -n "${NAMESPACE}" -o wide
echo ""
kubectl get pods -n "${MONITORING_NS}" -o wide
echo ""
echo "Access points:"
echo "  API:        http://<node-ip>:30080/health"
echo "  Grafana:    http://<node-ip>:30030  (admin/admin)"
echo "  Prometheus: http://<node-ip>:30090"

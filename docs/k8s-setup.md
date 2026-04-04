# K3s HA Cluster Setup Guide

This guide sets up a 3-node K3s high-availability cluster with embedded etcd, running the URL Shortener API, PostgreSQL, Valkey, and a full monitoring stack (Prometheus, Grafana, Loki, Alertmanager).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  K3s HA Cluster (3 server nodes, embedded etcd)                 │
│                                                                 │
│  Node .110            Node .111            Node .112            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ API pod      │    │ API pod      │    │ API pod      │     │
│  │ PostgreSQL   │    │              │    │              │     │
│  │ Valkey        │    │              │    │              │     │
│  │ GH Runner    │    │              │    │              │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                 │
│  Prometheus + Grafana + Loki + Alertmanager (monitoring ns)    │
│                                                                 │
│  NodePort: 30080 (API), 30030 (Grafana), 30090 (Prometheus)   │
└─────────────────────────────────────────────────────────────────┘
```

- **API**: 3 replicas with pod anti-affinity (1 per node) — survives any single node failure
- **PostgreSQL**: Pinned to Node .110 for data consistency (single-node stateful workload)
- **Valkey**: Single replica cache with graceful fallback
- **Monitoring**: Prometheus scrapes `/metrics` from all API pods

## Prerequisites

### Hardware
- 3x Ubuntu 24.04 Server machines on the same LAN
- Minimum 2GB RAM, 2 CPU cores each
- User `k9` with sudo access on all nodes

### Network
Ensure these ports are open between all nodes:

| Port | Protocol | Purpose |
|------|----------|---------|
| 6443 | TCP | K3s API server |
| 2379-2380 | TCP | etcd client/peer |
| 10250 | TCP | Kubelet metrics |
| 8472 | UDP | VXLAN (Flannel) |
| 51820 | UDP | WireGuard (if enabled) |

## Step 1: Install K3s HA Cluster

Choose a shared secret token (any random string):

```bash
export K3S_TOKEN="my-secret-token-change-me"
```

### Node 1 (192.168.1.110) — Initialize cluster

```bash
ssh k9@192.168.1.110

curl -sfL https://get.k3s.io | K3S_TOKEN=$K3S_TOKEN \
  sh -s - server \
  --cluster-init \
  --tls-san 192.168.1.110 \
  --tls-san 192.168.1.111 \
  --tls-san 192.168.1.112

# Verify it's running
sudo k3s kubectl get nodes
```

### Node 2 (192.168.1.111) — Join cluster

```bash
ssh k9@192.168.1.111

curl -sfL https://get.k3s.io | K3S_TOKEN=$K3S_TOKEN \
  sh -s - server \
  --server https://192.168.1.110:6443
```

### Node 3 (192.168.1.112) — Join cluster

```bash
ssh k9@192.168.1.112

curl -sfL https://get.k3s.io | K3S_TOKEN=$K3S_TOKEN \
  sh -s - server \
  --server https://192.168.1.110:6443
```

### Verify all nodes

```bash
# On any node
sudo k3s kubectl get nodes
# All 3 should show "Ready"
```

## Step 2: Configure kubectl Locally

Copy the kubeconfig from Node 1 to your local machine:

```bash
# On Node 1
sudo cat /etc/rancher/k3s/k3s.yaml

# On your local machine, save the output and replace 127.0.0.1 with 192.168.1.110:
mkdir -p ~/.kube
scp k9@192.168.1.110:/etc/rancher/k3s/k3s.yaml ~/.kube/config
sed -i 's/127.0.0.1/192.168.1.110/' ~/.kube/config

# Verify
kubectl get nodes
```

## Step 3: Label Nodes

Label Node 1 for PostgreSQL placement:

```bash
# Get node names
kubectl get nodes

# Label the .110 node for database workloads
kubectl label node <node-110-name> role=db
```

## Step 4: Create Namespaces and Secrets

```bash
# Apply namespaces
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/monitoring/namespace.yaml

# Create GHCR pull secret (private repo)
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=<your-github-username> \
  --docker-password=<your-github-pat> \
  -n url-shortener

# Create database credentials
# Copy the example and edit the base64 values:
cp k8s/secrets.yaml.example k8s/secrets.yaml
# Edit k8s/secrets.yaml with your password (base64 encoded)
# echo -n 'your-password' | base64
kubectl apply -f k8s/secrets.yaml
```

### Creating a GitHub Personal Access Token (PAT)

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `read:packages` scope
3. Use this token as `--docker-password` above

## Step 5: Deploy Application Stack

```bash
# Apply in order (or use the deploy script)
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/valkey-deployment.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml

# Wait for pods to be ready
kubectl get pods -n url-shortener -w
```

Or use the convenience script:

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

## Step 6: Deploy Monitoring Stack

```bash
# Prometheus
kubectl apply -f k8s/monitoring/prometheus-config.yaml
kubectl apply -f k8s/monitoring/alert-rules-config.yaml
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml

# Alertmanager
kubectl apply -f k8s/monitoring/alertmanager-config.yaml
kubectl apply -f k8s/monitoring/alertmanager-deployment.yaml

# Loki (log aggregation)
kubectl apply -f k8s/monitoring/loki-config.yaml
kubectl apply -f k8s/monitoring/loki-deployment.yaml

# Promtail (log collector — runs on every node)
kubectl apply -f k8s/monitoring/promtail-config.yaml
kubectl apply -f k8s/monitoring/promtail-daemonset.yaml

# Grafana dashboard ConfigMap (from JSON file)
kubectl create configmap grafana-dashboards \
  --from-file=url-shortener.json=docs/IncidentReportQuest/grafanaDashboard.json \
  -n monitoring --dry-run=client -o yaml | kubectl apply -f -

# Grafana
kubectl apply -f k8s/monitoring/grafana-deployment.yaml

# Verify
kubectl get pods -n monitoring
```

## Step 7: Set Up Self-Hosted GitHub Actions Runner

The servers are behind NAT, so we use a self-hosted runner on Node .110 for automated deployments.

### On Node .110:

```bash
ssh k9@192.168.1.110

# Create a directory for the runner
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download the latest runner (check https://github.com/actions/runner/releases for latest)
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz
tar xzf actions-runner-linux-x64.tar.gz
```

### Register the runner:

1. Go to your GitHub repo → Settings → Actions → Runners → New self-hosted runner
2. Copy the token from the setup page
3. Run on Node .110:

```bash
./config.sh --url https://github.com/cyanghxst/pe-hackathon \
  --token <TOKEN-FROM-GITHUB>
```

### Configure kubectl access for the runner:

```bash
# The runner user needs kubectl access
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config

# Verify
kubectl get nodes
```

### Install as a service (runs on boot):

```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

## Step 8: Verify Everything

### API Health

```bash
# All three nodes should respond
curl http://192.168.1.110:30080/health
curl http://192.168.1.111:30080/health
curl http://192.168.1.112:30080/health
# Expected: {"status":"ok"}
```

### Prometheus Metrics

```bash
# App metrics endpoint
curl http://192.168.1.110:30080/metrics

# Prometheus UI
open http://192.168.1.110:30090
# Check Status → Targets — flask_app job should show 3 endpoints UP
```

### Grafana Dashboard

```
URL:      http://192.168.1.110:30030
Username: admin
Password: admin
```

### Pod Distribution

```bash
kubectl get pods -n url-shortener -o wide
# Should show 3 url-shortener pods on 3 different nodes
# 1 postgres pod on the .110 node
# 1 valkey pod
```

## Step 9: HA Verification

1. Verify all 3 API endpoints respond:
   ```bash
   for ip in 110 111 112; do
     echo "Node .$ip:"; curl -s http://192.168.1.$ip:30080/health; echo
   done
   ```

2. If a node goes down (**.111 or .112**, NOT .110 — that runs PostgreSQL and Valkey):
   ```bash
   kubectl get nodes
   # Offline node shows "NotReady"

   kubectl get pods -n url-shortener -o wide
   # 2 API pods running, 1 in Unknown/Terminating state
   ```

3. Remaining nodes continue serving traffic:
   ```bash
   curl http://192.168.1.110:30080/health
   curl http://192.168.1.<remaining-node>:30080/health
   ```

4. When the node comes back online, it rejoins the cluster automatically.

## Troubleshooting

### Pods stuck in ImagePullBackOff
The GHCR pull secret is missing or incorrect:
```bash
kubectl describe pod <pod-name> -n url-shortener
# Check Events section for auth errors
kubectl delete secret ghcr-pull-secret -n url-shortener
# Recreate with correct credentials (Step 4)
```

### PostgreSQL pod not scheduling
The node label is missing:
```bash
kubectl get nodes --show-labels | grep role
kubectl label node <node-name> role=db
```

### API pods not starting (CrashLoopBackOff)
Check logs:
```bash
kubectl logs <pod-name> -n url-shortener
# Usually a database connection issue — verify postgres is running first
kubectl get pods -n url-shortener | grep postgres
```

### K3s node won't join
Check the token matches and Node 1 is reachable:
```bash
curl -k https://192.168.1.110:6443
# Should return "Unauthorized" (means the API server is up)
```

### Reset and start fresh
```bash
# On each node
/usr/local/bin/k3s-uninstall.sh
# Then re-run the install steps
```

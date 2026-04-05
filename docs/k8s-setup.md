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
│  │ PG primary   │    │ PG replica   │    │ PG replica   │     │
│  │ Valkey master│    │ Valkey repl  │    │ Valkey repl  │     │
│  │ Sentinel     │    │ Sentinel     │    │ Sentinel     │     │
│  │ GH Runner    │    │              │    │              │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                 │
│  CloudNativePG operator (cnpg-system ns)                       │
│  Prometheus + Grafana + Loki + Alertmanager (monitoring ns)    │
│                                                                 │
│  NodePort: 30080 (API), 30030 (Grafana), 30090 (Prometheus)   │
└─────────────────────────────────────────────────────────────────┘
```

- **API**: 3 replicas with pod anti-affinity (1 per node) — survives any single node failure
- **PostgreSQL**: 3-instance CloudNativePG cluster (1 primary + 2 replicas) with automatic failover — survives any single node failure
- **Valkey**: 3-node Sentinel HA (1 master + 2 replicas + 3 sentinels) with automatic failover, graceful fallback in app
- **Monitoring**: Prometheus scrapes `/metrics` from all API pods and PostgreSQL instances

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

## Step 3: Install Helm

Helm is required to install the CloudNativePG operator.

### Option A: Install script (recommended)

```bash
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4
chmod 700 get_helm.sh
./get_helm.sh
```

### Option B: Apt (Debian/Ubuntu)

```bash
sudo apt-get install curl gpg apt-transport-https --yes
curl -fsSL https://packages.buildkite.com/helm-linux/helm-debian/gpgkey | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/helm.gpg] https://packages.buildkite.com/helm-linux/helm-debian/any/ any main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt-get update
sudo apt-get install helm
```

### Option C: Snap

```bash
sudo snap install helm --classic
```

### Verify

```bash
helm version
```

## Step 4: Label Nodes and Install CloudNativePG Operator

Label all database nodes and install the CNPG operator:

```bash
# Get node names
kubectl get nodes

# Label all nodes for database workloads
kubectl label node <node-110-name> role=db
kubectl label node <node-111-name> role=db
kubectl label node <node-112-name> role=db

# Install CloudNativePG operator via Helm
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm repo update
helm install cnpg cnpg/cloudnative-pg -n cnpg-system --create-namespace

# Verify the operator is running
kubectl get pods -n cnpg-system
```

## Step 5: Create Namespaces and Secrets

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

## Step 6: Deploy Application Stack

```bash
# Apply in order (or use the deploy script)
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres-cluster.yaml

# Deploy Valkey HA (Sentinel mode) via Helm
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm upgrade --install valkey bitnami/valkey \
  -n url-shortener \
  -f k8s/valkey-values.yaml

# Wait for the PostgreSQL cluster to be ready (1 primary + 2 replicas)
kubectl get cluster -n url-shortener -w
# STATUS should show "Cluster in healthy state"

kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml

# Wait for all pods to be ready
kubectl get pods -n url-shortener -w
```

Or use the convenience script:

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

## Step 7: Deploy Monitoring Stack

```bash
chmod +x scripts/deploy-monitoring.sh
./scripts/deploy-monitoring.sh
```

Monitoring configs live in `monitoring/` (single source of truth for both Docker Compose and K8s).
The script generates K8s ConfigMaps from those files and applies the workload manifests from `k8s/monitoring/`.

## Step 8: Set Up Self-Hosted GitHub Actions Runner

The servers are behind NAT, so we use a [self-hosted runner](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners) on Node .110 for automated deployments.

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

## Step 9: Verify Everything

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

### PostgreSQL Cluster Health

```bash
# Check CNPG cluster status
kubectl get cluster -n url-shortener
# STATUS should show "Cluster in healthy state", READY "3/3"

# Check which instance is the primary
kubectl get pods -n url-shortener -l cnpg.io/cluster=postgres-cluster \
  -o custom-columns=NAME:.metadata.name,ROLE:.metadata.labels.role,NODE:.spec.nodeName
```

### Pod Distribution

```bash
kubectl get pods -n url-shortener -o wide
# Should show 3 url-shortener pods on 3 different nodes
# 3 postgres-cluster pods (1 primary + 2 replicas)
# 3 valkey-node pods (1 master + 2 replicas, each with sentinel sidecar)
```

## Step 10: HA Verification

1. Verify all 3 API endpoints respond:
   ```bash
   for ip in 110 111 112; do
     echo "Node .$ip:"; curl -s http://192.168.1.$ip:30080/health; echo
   done
   ```

2. Verify PostgreSQL HA — if **any** node goes down:
   ```bash
   kubectl get nodes
   # Offline node shows "NotReady"

   kubectl get pods -n url-shortener -o wide
   # 2 API pods running, 1 in Unknown/Terminating state

   # CNPG handles PostgreSQL failover automatically:
   kubectl get cluster -n url-shortener
   # If the primary node went down, a replica is promoted within ~30s

   # Check the new primary
   kubectl get pods -n url-shortener -l cnpg.io/cluster=postgres-cluster \
     -o custom-columns=NAME:.metadata.name,ROLE:.metadata.labels.role
   ```

3. Remaining nodes continue serving traffic (including database writes):
   ```bash
   curl http://192.168.1.<remaining-node-1>:30080/health
   curl http://192.168.1.<remaining-node-2>:30080/health
   ```

4. When the node comes back online, it rejoins the cluster automatically. CNPG will re-add the PostgreSQL instance as a replica.

## Troubleshooting

### Pods stuck in ImagePullBackOff
The GHCR pull secret is missing or incorrect:
```bash
kubectl describe pod <pod-name> -n url-shortener
# Check Events section for auth errors
kubectl delete secret ghcr-pull-secret -n url-shortener
# Recreate with correct credentials (Step 4)
```

### PostgreSQL cluster not healthy
Check CNPG operator logs and cluster status:
```bash
# Check cluster status
kubectl get cluster -n url-shortener
kubectl describe cluster postgres-cluster -n url-shortener

# Check operator logs
kubectl logs -n cnpg-system -l app.kubernetes.io/name=cloudnative-pg

# Check individual pod logs
kubectl logs postgres-cluster-1 -n url-shortener
```

### PostgreSQL pods not scheduling
Node labels may be missing:
```bash
kubectl get nodes --show-labels | grep role
kubectl label node <node-name> role=db
```

### CNPG operator not installed
```bash
# Verify the operator is running
kubectl get pods -n cnpg-system
# If empty, install it:
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm install cnpg cnpg/cloudnative-pg -n cnpg-system --create-namespace
```

### API pods not starting (CrashLoopBackOff)
Check logs:
```bash
kubectl logs <pod-name> -n url-shortener
# Usually a database connection issue — verify postgres cluster is healthy first
kubectl get cluster -n url-shortener
kubectl get pods -n url-shortener -l cnpg.io/cluster=postgres-cluster
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

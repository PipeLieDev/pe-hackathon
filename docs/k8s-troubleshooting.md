# K3s Troubleshooting

Common issues and fixes for the K3s cluster. See [k8s-setup.md](k8s-setup.md) for the full setup guide.

## Pods stuck in ImagePullBackOff

The GHCR pull secret is missing or incorrect:

```bash
kubectl describe pod <pod-name> -n url-shortener
# Check Events section for auth errors
kubectl delete secret ghcr-pull-secret -n url-shortener
# Recreate with correct credentials (Step 5 in setup guide)
```

## PostgreSQL cluster not healthy

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

## PostgreSQL pods not scheduling

Node labels may be missing:

```bash
kubectl get nodes --show-labels | grep role
kubectl label node <node-name> role=db
```

## CNPG operator not installed

```bash
# Verify the operator is running
kubectl get pods -n cnpg-system
# If empty, install it:
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm install cnpg cnpg/cloudnative-pg -n cnpg-system --create-namespace
```

## API pods not starting (CrashLoopBackOff)

Check logs:

```bash
kubectl logs <pod-name> -n url-shortener
# Usually a database connection issue — verify postgres cluster is healthy first
kubectl get cluster -n url-shortener
kubectl get pods -n url-shortener -l cnpg.io/cluster=postgres-cluster
```

## K3s node won't join

Check the token matches and Node 1 is reachable:

```bash
curl -k https://192.168.1.110:6443
# Should return "Unauthorized" (means the API server is up)
```

## Reset and start fresh

```bash
# On each node
/usr/local/bin/k3s-uninstall.sh
# Then re-run the install steps
```

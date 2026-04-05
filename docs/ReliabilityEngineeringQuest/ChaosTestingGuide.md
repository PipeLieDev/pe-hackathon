# Chaos Testing Guide

Commands to simulate failures in the Kubernetes cluster and verify recovery. All resources live in the `url-shortener` namespace.

**Tip:** Open a second terminal and run this to watch recovery in real time:

```bash
kubectl get pods -n url-shortener -w
```

---

## 1. Kill a Single App Pod

Simulates an app crash. Kubernetes should restart it while the other 2 replicas keep serving.

```bash
# Pick a pod
kubectl get pods -n url-shortener -l app=url-shortener

# Kill it
kubectl delete pod <pod-name> -n url-shortener

# Watch it come back
kubectl get pods -n url-shortener -l app=url-shortener -w
```

**Verify:** Hit the API while the pod is restarting — it should still respond via the remaining pods:

```bash
curl http://<node-ip>:30080/health
```

---

## 2. Kill All App Pods at Once

Simulates a full app outage. Kubernetes should restart all 3 pods.

```bash
kubectl delete pods -n url-shortener -l app=url-shortener
```

**Verify:** Requests will fail briefly, then recover once at least one pod passes its readiness probe (15s initial delay, then every 5s).

```bash
# Loop to observe downtime and recovery
while true; do curl -s -o /dev/null -w "%{http_code} " http://<node-ip>:30080/health; sleep 1; done
```

---

## 3. Kill the Valkey (Cache) Pod

Simulates cache failure. The app should continue working — just without caching.

```bash
kubectl delete pod -n url-shortener -l app=valkey
```

**Verify:** The API should still respond. Check the `X-Cache` header — it should be `MISS` on every request:

```bash
curl -v http://<node-ip>:30080/users 2>&1 | grep X-Cache
```

---

## 4. Kill a PostgreSQL Pod

Simulates a database node failure. CloudNativePG (3 instances) should handle failover.

```bash
# List postgres pods
kubectl get pods -n url-shortener -l cnpg.io/cluster=postgres-cluster

# Kill the primary (usually the one with role=primary)
kubectl get pods -n url-shortener -l cnpg.io/cluster=postgres-cluster -L role

# Delete the primary pod
kubectl delete pod <primary-pod-name> -n url-shortener
```

**Verify:** There will be a brief period of 500 errors during failover. Once a replica is promoted, requests should work again:

```bash
# Watch the cluster status
kubectl get cluster postgres-cluster -n url-shortener -w

# Test the API
curl http://<node-ip>:30080/users
```

---

## 5. Simulate OOM Kill (Memory Pressure)

Force an app pod to exceed its 512Mi memory limit.

```bash
# Exec into a pod
kubectl exec -it <pod-name> -n url-shortener -- /bin/sh

# Allocate memory until OOM (this will get the pod killed)
python3 -c "x = ' ' * (1024 * 1024 * 600)"
```

**Verify:** The pod should show `OOMKilled` status and then restart automatically:

```bash
kubectl get pods -n url-shortener -l app=url-shortener
# Look for RESTARTS column incrementing and STATUS showing OOMKilled briefly
```

---

## 6. Simulate Liveness Probe Failure

Make the `/health` endpoint unreachable by overloading the pod. After 5 failed checks (10s apart), Kubernetes will restart it.

```bash
# Scale down to 1 replica so you can observe the effect clearly
kubectl scale deployment url-shortener -n url-shortener --replicas=1

# Exec into the pod and block port 5000 (requires net-admin or iptables)
# Alternatively, just kill the gunicorn/flask process inside the container:
kubectl exec -it <pod-name> -n url-shortener -- /bin/sh -c "kill 1"
```

**Verify:** Pod restarts after liveness probe failures:

```bash
kubectl describe pod <pod-name> -n url-shortener | grep -A5 "Last State"
```

**Restore replicas:**

```bash
kubectl scale deployment url-shortener -n url-shortener --replicas=3
```

---

## 7. Simulate a Bad Deployment (Rolling Update Failure)

Deploy a broken image and watch the rollout stall without taking down healthy pods.

```bash
# Set a non-existent image tag
kubectl set image deployment/url-shortener url-shortener=ghcr.io/pipeliedev/pe-hackathon:broken -n url-shortener

# Watch the rollout — it should stall with new pods in ImagePullBackOff
kubectl rollout status deployment/url-shortener -n url-shortener --timeout=30s

# Existing pods should still be running
kubectl get pods -n url-shortener -l app=url-shortener

# Verify the API still works (served by old pods)
curl http://<node-ip>:30080/health

# Roll back
kubectl rollout undo deployment/url-shortener -n url-shortener
```

---

## Quick Reference

| Test | Command | Expected Recovery Time |
|---|---|---|
| Kill 1 app pod | `kubectl delete pod <name> -n url-shortener` | ~15-20s (readiness probe) |
| Kill all app pods | `kubectl delete pods -l app=url-shortener -n url-shortener` | ~15-20s |
| Kill Valkey | `kubectl delete pod -l app=valkey -n url-shortener` | Instant (cache bypassed) |
| Kill Postgres primary | `kubectl delete pod <primary> -n url-shortener` | ~10-30s (CNPG failover) |
| OOM kill | Exceed 512Mi in pod | ~15-20s (auto restart) |
| Bad deploy | `kubectl set image ... :broken` | No downtime (rollout stalls) |
| Rollback | `kubectl rollout undo deployment/url-shortener -n url-shortener` | ~15-20s |

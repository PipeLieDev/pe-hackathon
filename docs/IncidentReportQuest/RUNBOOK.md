# Incident Response Runbook

## Service Endpoints

| Service | URL |
|---|---|
| App | `http://192.168.1.112:30080` (or .110, .111) |
| Prometheus | `http://192.168.1.112:30090` (or .110, .111) |
| Grafana | `http://192.168.1.112:30030` (or .110, .111) |
| Alertmanager | `kubectl port-forward svc/alertmanager-svc -n monitoring 9093:9093` → `http://localhost:9093` |

Find node IPs: `kubectl get nodes -o wide`

---

## When an Alert Fires

1. **Confirm** — Open Alertmanager and identify the alert name, severity, and affected target
2. **Assess** — Check pod state and Prometheus targets:
   - `kubectl get pods -n url-shortener -o wide`
   - Prometheus targets page: `<prometheus-url>/targets`
3. **Triage** — Jump to the relevant section below
4. **Resolve** — Apply fix, verify alert clears, document root cause

---

## Service Down Alert

> `ServiceDown` — app instance not reachable

Prometheus cannot scrape the app. Pod is likely crashed, pending, or not listening.

**Investigate**:
1. `kubectl get pods -n url-shortener -o wide`
2. `kubectl logs <pod-name> -n url-shortener --previous` (if CrashLoopBackOff)
3. `kubectl describe deployment url-shortener -n url-shortener`
4. `kubectl exec -n url-shortener <pod-name> -- pg_isready -h postgres-cluster-rw -U postgres`
5. `kubectl describe node <node-name>` (if pods stuck in Pending)

**Common causes**:
- CrashLoopBackOff → config or dependency error in logs
- Pending → insufficient node resources
- OOMKilled → pod exceeded memory limits

**Fix**:
- Delete pod to let deployment recreate it: `kubectl delete pod <pod-name> -n url-shortener`
- Or restart deployment: `kubectl rollout restart deployment/url-shortener -n url-shortener`
- If recurring, fix root cause from logs and redeploy

---

## High Error Rate Alert

> `HighErrorRate` — > 5% 5xx error rate for 2 minutes

**Investigate**:
1. `kubectl logs -n url-shortener -l app=url-shortener --tail 100 | grep -i error`
2. Check Grafana for failing endpoint patterns
3. `kubectl get cluster -n url-shortener` (database health)
4. `kubectl exec -n url-shortener <pod-name> -- redis-cli -h valkey ping` (Valkey health)
5. `kubectl top pods -n url-shortener`

**Common causes**:
- Database connection failures
- Code exceptions or bad deployments
- Dependency timeouts

**Fix**:
- Roll back if caused by recent deploy: `kubectl rollout undo deployment/url-shortener -n url-shortener`
- Fix failing code or configuration and redeploy

---

## High Latency Alert

> `HighLatency` — p95 request latency > 2 seconds for 2 minutes

**Investigate**:
1. `kubectl top pods -n url-shortener`
2. `kubectl top nodes`
3. Check Grafana latency panels
4. `kubectl exec -n url-shortener postgres-cluster-1 -- pg_stat_activity` (slow queries)
5. `kubectl exec -n url-shortener valkey-node-0 -- redis-cli info stats`

**Common causes**:
- Slow database queries
- High CPU/memory usage
- Network or I/O bottlenecks

**Fix**:
- Scale up to reduce load: `kubectl scale deployment url-shortener -n url-shortener --replicas=4`
- Document slow queries or bottlenecks found for follow-up fix after the incident

---

## HA Scenarios

**Node Failure**:
- `kubectl get nodes` — look for NotReady
- `kubectl describe node <node-name>` to investigate
- Pods auto-reschedule to healthy nodes; monitor with `kubectl get pods -n url-shortener -w`

**Database Failover**:
- `kubectl get cluster -n url-shortener` — check cluster health
- `kubectl logs -n cnpg-system -l app.kubernetes.io/name=cloudnative-pg --follow` — monitor failover
- Verify new primary: `kubectl get pods -n url-shortener -l cnpg.io/cluster=postgres-cluster -o custom-columns=NAME:.metadata.name,ROLE:.metadata.labels.role`

**Valkey Sentinel Failover**:
- `kubectl get pods -n url-shortener -l app.kubernetes.io/name=valkey`
- `kubectl logs -n url-shortener valkey-node-0 -c sentinel`
- Verify master: `kubectl exec -n url-shortener valkey-node-0 -- redis-cli -p 26379 sentinel masters`

---

## Post-Incident

- Document root cause and fix
- Update alert thresholds if needed
- Review whether the alert was useful signal or noise

---

## Troubleshooting Access

**Cannot reach NodePort services:**
- Check firewall allows ports 30080, 30090, 30030
- `ping 192.168.1.112` — verify node is reachable
- `kubectl get svc -n monitoring -o wide` — confirm services are exposed
- Try other node IPs (.110, .111) if one is down

**Alertmanager port-forward not working:**
- `kubectl get svc -n monitoring` — verify service exists
- `kubectl get pods -n monitoring` — verify pod is running

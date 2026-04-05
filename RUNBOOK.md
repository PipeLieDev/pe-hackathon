# Incident Response Runbook

## In Case of Emergency

When an alert fires, follow this checklist in order:

1. **Access the environment**
   - Access services via NodePorts:
     - Prometheus: `http://192.168.1.112:30090` (or .110, .111)
     - Grafana: `http://192.168.1.112:30030` (or .110, .111)
     - App: `http://192.168.1.112:30080` (or .110, .111)
     - Alertmanager: Run `kubectl port-forward svc/alertmanager-svc -n monitoring 9093:9093`, then access `http://localhost:9093`

2. **Confirm the alert**
   - Check Prometheus targets: `http://192.168.1.112:30090/targets`
   - Check Grafana dashboards: `http://192.168.1.112:30030`
   - For Alertmanager: Run `kubectl port-forward svc/alertmanager-svc -n monitoring 9093:9093`, then access `http://localhost:9093`
   - Identify alert name, severity, affected target, and status

3. **Check current service state**
   - Check pods: `kubectl get pods -n url-shortener -o wide`
   - Confirm Prometheus target status: `http://192.168.1.112:30090/targets`

4. **Capture evidence**
   - Save the alert details and timestamps
   - Collect relevant logs and metrics screenshots

5. **Triage by alert type**
   - ServiceDown → check pod availability
   - HighErrorRate → inspect app errors and traffic patterns
   - HighLatency → inspect resource usage and slow queries

6. **Resolve and document**
   - Apply fix, then verify the alert returns to normal
   - Note root cause, resolution, and next preventative action

---

## Service Down Alert

**Symptoms**: Prometheus alert `ServiceDown` fired (app instance not reachable)

**What it means**: Prometheus cannot scrape a Flask app target. This usually means the pod is crashed, unreachable, or the service is not listening.

**Immediate Actions**:
1. Check pod status: `kubectl get pods -n url-shortener -o wide`
2. If pod is in CrashLoopBackOff, check logs: `kubectl logs <pod-name> -n url-shortener --previous`
3. Check deployment events: `kubectl describe deployment url-shortener -n url-shortener`
4. Verify database connectivity: `kubectl exec -n url-shortener <pod-name> -- pg_isready -h postgres-cluster-rw -U postgres`
5. Check node resources if pods can't schedule: `kubectl describe node <node-name>`

**Diagnosis**:
- CrashLoopBackOff: app is crashing on startup — check logs for config or dependency errors
- Pending pods: insufficient resources or scheduling constraints
- OOMKilled: pod exceeded memory limits
- DNS failure: target name not resolvable inside the cluster

**Resolution**:
- Restart the pod: `kubectl delete pod <pod-name> -n url-shortener` (deployment will recreate it)
- Restart the deployment: `kubectl rollout restart deployment/url-shortener -n url-shortener`
- If the app repeatedly crashes, fix the root cause from logs and redeploy

---

## High Error Rate Alert

**Symptoms**: `HighErrorRate` fired (> 5% 5xx error rate for 2 minutes)

**What it means**: A high percentage of requests returned 5xx responses over the last 5 minutes.

**Immediate Actions**:
1. Check logs from all app pods: `kubectl logs -n url-shortener -l app=url-shortener --tail 100 | grep -i error`
2. Identify failing request patterns in Grafana (`http://192.168.1.112:30030`)
3. Confirm if the issue is isolated to a single endpoint or system-wide
4. Check database cluster health: `kubectl get cluster -n url-shortener`
5. Verify Valkey connectivity: `kubectl exec -n url-shortener <pod-name> -- redis-cli -h valkey ping`
6. Check pod resource usage: `kubectl top pods -n url-shortener`

**Diagnosis**:
- Database connection failures
- API or code exceptions
- Bad request payloads or validation issues
- Dependency timeouts / upstream failures

**Resolution**:
- Fix the failing code or configuration
- Roll back deployment if needed: `kubectl rollout undo deployment/url-shortener -n url-shortener`
- Restart app services after the root cause is fixed

---

## High Latency Alert

**Symptoms**: `HighLatency` fired (95th percentile request latency > 2 seconds for 2 minutes)

**What it means**: The 95th percentile request latency is above the configured threshold, indicating slow responses.

**Immediate Actions**:
1. Check pod resource usage: `kubectl top pods -n url-shortener`
2. Check node resources: `kubectl top nodes`
3. Review app performance metrics in Grafana (`http://192.168.1.112:30030`)
4. Check database performance: `kubectl exec -n url-shortener postgres-cluster-1 -- pg_stat_activity`
5. Review Valkey performance: `kubectl exec -n url-shortener valkey-node-0 -- redis-cli info stats`

**Diagnosis**:
- Slow database queries
- High CPU or memory usage
- Network latency or I/O waits
- Backpressure from downstream services

**Resolution**:
- Optimize the slow path or query
- Scale deployment if needed: `kubectl scale deployment url-shortener -n url-shortener --replicas=4`
- Add caching if appropriate

---

## HA Scenarios

**Node Failure**:
- Symptoms: Multiple pods become unavailable, alerts fire for affected services
- Check node status: `kubectl get nodes`
- If node is NotReady, investigate: `kubectl describe node <node-name>`
- Pods will automatically reschedule to healthy nodes (if anti-affinity allows)
- Monitor cluster recovery: `kubectl get pods -n url-shortener -w`

**Database Failover**:
- Symptoms: PostgreSQL cluster shows degraded status
- Check cluster health: `kubectl get cluster -n url-shortener`
- Monitor failover: `kubectl logs -n cnpg-system -l app.kubernetes.io/name=cloudnative-pg --follow`
- Verify new primary: `kubectl get pods -n url-shortener -l cnpg.io/cluster=postgres-cluster -o custom-columns=NAME:.metadata.name,ROLE:.metadata.labels.role`

**Valkey Sentinel Failover**:
- Symptoms: Cache operations fail, Valkey pods restart
- Check Valkey cluster: `kubectl get pods -n url-shortener -l app.kubernetes.io/name=valkey`
- Monitor Sentinel logs: `kubectl logs -n url-shortener valkey-node-0 -c sentinel`
- Verify master election: `kubectl exec -n url-shortener valkey-node-0 -- redis-cli -p 26379 sentinel masters`

---

## Common Emergency Commands

- Check pod status: `kubectl get pods -n url-shortener -o wide`
- Check logs: `kubectl logs -n url-shortener -l app=url-shortener --tail 100`
- Restart deployment: `kubectl rollout restart deployment/url-shortener -n url-shortener`
- Check node status: `kubectl get nodes`
- Check database cluster: `kubectl get cluster -n url-shortener`
- Access monitoring services via NodePorts:
  - Prometheus: `http://192.168.1.112:30090`
  - Grafana: `http://192.168.1.112:30030`
  - App: `http://192.168.1.112:30080`
  - Alertmanager: `kubectl port-forward svc/alertmanager-svc -n monitoring 9093:9093` then `http://localhost:9093`

To find the node IP:
- `kubectl get nodes -o wide`

---

## Post-Incident Notes

After the incident:
- Document the root cause and fix
- Update alert thresholds if needed
- Note any policy, deployment, or dependency changes
- Review whether the alert produced a useful signal or noise

---

## Troubleshooting Access Issues

**Cannot access NodePort services:**
- Verify firewall allows access to node ports (30080, 30090, 30030)
- Check if nodes are reachable: `ping 192.168.1.112`
- Confirm services are exposed: `kubectl get svc -n monitoring -o wide`
- Try different node IPs (.110, .111) if one node is down

**kubectl port-forward not working for Alertmanager:**
- Check if services exist: `kubectl get svc -n monitoring`
- Verify pods are running: `kubectl get pods -n monitoring`
- Check service selectors match pod labels

---

## Existing Alert Summaries

- `ServiceDown`: app instance not reachable
- `HighErrorRate`: > 5% 5xx error rate for 2 minutes
- `HighLatency`: 95th percentile request latency > 2 seconds for 2 minutes

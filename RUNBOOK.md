# Incident Response Runbook

## In Case of Emergency

**First, identify your environment:**
- **Docker Development**: If running `docker-compose ps` shows containers
- **Kubernetes Production**: If `kubectl get pods -n url-shortener` shows pods

When an alert fires, follow this checklist in order:

1. **Access the environment**
   - **Docker Development**: Ensure you're on the local machine with Docker running
   - **Kubernetes Production**: Access services directly via NodePorts:
     - Prometheus: `http://192.168.1.112:30090` (or .110, .111)
     - Grafana: `http://192.168.1.112:30030` (or .110, .111)
     - App: `http://192.168.1.112:30080` (or .110, .111)
     - Alertmanager: Run `kubectl port-forward svc/alertmanager-svc -n monitoring 9093:9093` from your local machine (with kubectl configured for the cluster), then access `http://localhost:9093`
     - For SSH access to run commands: `ssh k9@192.168.1.112` (ensure kubectl is configured)
   - Verify you have access to monitoring tools and can run diagnostic commands

2. **Confirm the alert**
   - **Docker**: Open Alertmanager: `http://localhost:9093`
   - **Kubernetes**: 
     - Use NodePort services: `http://192.168.1.112:30090` (Prometheus), `http://192.168.1.112:30030` (Grafana)
     - For Alertmanager: Run `kubectl port-forward svc/alertmanager-svc -n monitoring 9093:9093` from your local machine, then access `http://localhost:9093`
     - Check targets page to verify service status
   - Identify alert name, severity, affected target, and status
2. **Check current service state**
   - **Docker**: Confirm app containers: `docker ps --format 'table {{.Names}}\t{{.Status}}' | grep pe-hackathon-app`
   - **Kubernetes**: Check pods: `kubectl get pods -n url-shortener`
   - Confirm Prometheus target status: `http://localhost:9090/targets` (or `http://<node-ip>:30090/targets` in K8s)
3. **Capture evidence**
   - Save the alert details and timestamps
   - Collect relevant logs and metrics screenshots
4. **Triage by alert type**
   - ServiceDown → check container/pod availability
   - HighErrorRate → inspect app errors and traffic patterns
   - HighLatency → inspect resource usage and slow queries
5. **Resolve and document**
   - Apply fix, then verify the alert returns to normal
   - Note root cause, resolution, and next preventative action

---

## Service Down Alert

**Symptoms**: Prometheus alert `ServiceDown` fired

**What it means**: Prometheus cannot scrape a Flask app target. This usually means the app container is stopped, unreachable, or the service is not listening.

**Immediate Actions**:
1. Check app container state:
   - `docker ps -a --format 'table {{.Names}}\t{{.Status}}' | grep pe-hackathon-app`
2. If the container is stopped, inspect its logs:
   - `docker logs pe-hackathon-app1-1 --tail 50`
3. Confirm the target address resolves in the app network:
   - `docker exec pe-hackathon-prometheus-1 wget -qO- http://app1:5000/metrics`
4. Check if the app is listening on port 5000:
   - `docker exec pe-hackathon-app1-1 netstat -tlnp | grep 5000`
5. If the container is healthy but unreachable, check Docker networking and DNS.

**Diagnosis**:
- `Exited (0)` or similar: container was stopped cleanly
- `OOM killed` / `signal`: resource or process failure
- App startup error: configuration or dependency issue
- DNS failure: target name not resolvable inside Prometheus

**Resolution**:
- Restart the app container: `docker start pe-hackathon-app1-1`
- If using compose, restart the service: `docker-compose up -d app1`
- If the app repeatedly exits, fix the root cause from logs and restart

**Kubernetes Production Resolution**:
- Check pod status: `kubectl get pods -n url-shortener -o wide`
- If pod is in CrashLoopBackOff, check logs: `kubectl logs <pod-name> -n url-shortener --previous`
- Restart the pod: `kubectl delete pod <pod-name> -n url-shortener` (deployment will recreate it)
- If issue persists, check deployment events: `kubectl describe deployment url-shortener -n url-shortener`
- Verify database connectivity: `kubectl exec -n url-shortener <pod-name> -- pg_isready -h postgres-cluster-rw -U postgres`
- Check node resources if pods can't schedule: `kubectl describe node <node-name>`

---

## High Error Rate Alert

**Symptoms**: `HighErrorRate` fired

**What it means**: A high percentage of requests returned 5xx responses over the last 5 minutes.

**Immediate Actions**:
1. Check app error logs:
   - `docker logs pe-hackathon-app1-1 --tail 100 | grep -i error`
   - `docker logs pe-hackathon-app2-1 --tail 100 | grep -i error`
2. Identify failing request patterns in Grafana or Prometheus.
3. Confirm if the issue is isolated to a single endpoint or system-wide.
4. Check the database and external dependencies:
   - `docker exec pe-hackathon-db-1 pg_isready -U postgres`
   - `docker stats pe-hackathon-db-1`

**Diagnosis**:
- Database connection failures
- API or code exceptions
- Bad request payloads or validation issues
- Dependency timeouts / upstream failures

**Resolution**:
- Fix the failing code or configuration
- Roll back recent deployments if necessary
- Restart app services after the root cause is fixed

**Kubernetes Production Resolution**:
- Check logs from all app pods: `kubectl logs -n url-shortener -l app=url-shortener --tail 100 | grep -i error`
- If using Loki, query logs in Grafana for error patterns
- Check database cluster health: `kubectl get cluster -n url-shortener`
- Verify Valkey connectivity: `kubectl exec -n url-shortener <pod-name> -- redis-cli -h valkey ping`
- Roll back deployment if needed: `kubectl rollout undo deployment/url-shortener -n url-shortener`
- Check pod resource usage: `kubectl top pods -n url-shortener`

---

## High Latency Alert

**Symptoms**: `HighLatency` fired

**What it means**: The 95th percentile request latency is above the configured threshold, indicating slow responses.

**Immediate Actions**:
1. Check app performance metrics in Grafana.
2. Review database query latency and slow requests.
3. Check container resource usage:
   - `docker stats pe-hackathon-app1-1 pe-hackathon-app2-1 pe-hackathon-db-1`
4. Confirm if latency is caused by CPU, memory, or I/O bottlenecks.

**Diagnosis**:
- Slow database queries
- High CPU or memory usage
- Network latency or I/O waits
- Backpressure from downstream services

**Resolution**:
- Optimize the slow path or query
- Add caching if appropriate
- Scale resources or reduce load

**Kubernetes Production Resolution**:
- Check pod resource usage: `kubectl top pods -n url-shortener`
- Check node resources: `kubectl top nodes`
- Scale deployment if needed: `kubectl scale deployment url-shortener -n url-shortener --replicas=4`
- Check database performance: `kubectl exec -n url-shortener postgres-cluster-1 -- pg_stat_activity`
- Review Valkey performance: `kubectl exec -n url-shortener valkey-node-0 -- redis-cli info stats`
- Check network policies or service mesh if applicable

---

## Kubernetes HA Scenarios

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

### Docker Development
- Restart app service: `docker-compose restart app`
- Check logs for all app instances:
  - `docker logs pe-hackathon-app1-1 --tail 100`
  - `docker logs pe-hackathon-app2-1 --tail 100`
- Check Prometheus targets: `http://localhost:9090/targets`
- Check Alertmanager: `http://localhost:9093`
- Verify app metrics endpoint: `http://localhost:5000/metrics`

### Kubernetes Production
- Check pod status: `kubectl get pods -n url-shortener -o wide`
- Check logs: `kubectl logs -n url-shortener -l app=url-shortener --tail 100`
- Restart deployment: `kubectl rollout restart deployment/url-shortener -n url-shortener`
- Check node status: `kubectl get nodes`
- Access monitoring services via NodePorts:
  - Prometheus: `http://192.168.1.112:30090`
  - Grafana: `http://192.168.1.112:30030`
  - App: `http://192.168.1.112:30080`
  - Alertmanager: `kubectl port-forward svc/alertmanager-svc -n monitoring 9093:9093` then `http://localhost:9093`
- Check database cluster: `kubectl get cluster -n url-shortener`

## Kubernetes Production Endpoints

If using the Kubernetes production stack, use the node port endpoints:

- App: `http://<node-ip>:30080`
- Prometheus: `http://<node-ip>:30090`
- Grafana: `http://<node-ip>:30030`
- Alertmanager: port-forward with `kubectl port-forward svc/alertmanager-svc -n monitoring 9093:9093` then open `http://localhost:9093`

To find the node IP:
- `kubectl get nodes -o wide`

---

## Post-Incident Notes

After the incident:
- Document the root cause and fix
- Update alert thresholds if needed
- Note any policy, deployment, or dependency changes
- Review whether the alert produced a useful signal or noise

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
- Ensure you're running the command on a machine with kubectl access to the cluster

**SSH access issues:**
- Verify SSH key or password authentication
- Check if SSH service is running on target nodes
- Ensure firewall allows SSH (port 22)

## Existing Alert Summaries

Keep the following current as reference:
- `ServiceDown`: app instance not reachable
- `HighErrorRate`: > 5% 5xx error rate for 2 minutes
- `HighLatency`: 95th percentile request latency > 2 seconds for 2 minutes

# Incident Response Runbook

## Service Down Alert

**Symptoms**: Prometheus alert "ServiceDown" fired

**Immediate Actions**:
1. Check app container status: `docker ps | grep pe-hackathon-app`
2. View app logs: `docker logs pe-hackathon-app-1`
3. Check database connectivity: `docker exec pe-hackathon-db-1 pg_isready -U postgres`

**Diagnosis**:
- If container stopped: Check for OOM kills or crashes in logs
- If database unreachable: Restart database or check network
- If app logs show errors: Check configuration or dependencies

**Resolution**:
- Restart app: `docker-compose restart app`
- If persistent: Check environment variables and dependencies

## High Error Rate Alert

**Symptoms**: Error rate > 10% for 2+ minutes

**Immediate Actions**:
1. Check error logs: `docker logs pe-hackathon-app-1 | grep ERROR`
2. Identify failing endpoints in Grafana dashboard
3. Check database performance: `docker stats pe-hackathon-db-1`

**Diagnosis**:
- Database connection issues
- Invalid requests/data
- Code bugs in error-prone endpoints

**Resolution**:
- Fix code issues if identified
- Scale database if overloaded
- Add request validation

## High Latency Alert

**Symptoms**: 95th percentile latency > 2 seconds

**Immediate Actions**:
1. Check slow endpoints in Grafana
2. Monitor database query performance
3. Check system resources: `docker stats`

**Diagnosis**:
- Slow database queries
- Memory/CPU constraints
- Network issues

**Resolution**:
- Optimize slow queries
- Add database indexes
- Scale resources if needed

## Business Metrics Alerts (Grafana)

**Low User Registration**: User count not increasing
- Check user creation endpoint
- Verify database writes
- Check for spam protection blocks

**High URL Creation Rate**: Sudden spike in URL creation
- Monitor for abuse/bot activity
- Check rate limiting
- Scale if legitimate traffic

## General Troubleshooting

**Log Access**: `docker logs pe-hackathon-app-1`

**Metrics Access**:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- App Metrics: http://localhost:5000/metrics

**Database Access**: Connect via pgAdmin or `psql` in container

**Testing Alerts**:
- Stop app container to trigger ServiceDown
- Make invalid requests to trigger HighErrorRate
- Add artificial delays to trigger HighLatency
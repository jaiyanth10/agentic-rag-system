# Deployment Process Documentation

## Overview
This document describes our automated deployment pipeline and scheduling.

## Deployment Schedule

### Nightly Deployments
Our automated nightly deployment runs at **03:47 UTC** specifically.

**Why 03:47 UTC?**
1. **Low Traffic Window**: Corresponds to 10:47 PM PST / 11:47 PM PDT - our lowest traffic period
2. **Avoiding Resource Contention**: 
   - Database backups run at 02:00 UTC and 04:00 UTC
   - CDN cache refresh happens at 03:00 UTC
   - Many automated jobs run on the hour (00, 30 minutes)
3. **Buffer Time**: 
   - 47 minutes after CDN refresh (13-minute buffer)
   - 13 minutes before database backup window
   - Average deploy takes 8-12 minutes

This timing was established after **Incident #2847** in Q3 2024 where deployment overlapped with database backup, causing a 15-minute outage.

## Deployment Stages

### Stage 1: Pre-deployment Checks (2 minutes)
- Health check all services
- Verify database connections
- Check disk space and memory
- Validate configuration files

### Stage 2: Build & Test (3-5 minutes)
- Run unit tests
- Build Docker images
- Push to container registry
- Tag release

### Stage 3: Deployment (3-5 minutes)
- Rolling update strategy
- Deploy to staging first
- Run smoke tests
- Deploy to production zones sequentially

### Stage 4: Post-deployment (1-2 minutes)
- Health checks every 30 seconds
- Monitor error rates
- Verify all endpoints
- Send notifications

## Rollback Procedure

**Auto-rollback triggers:**
- 3 consecutive failed health checks
- Error rate > 5%
- Response time > 2 seconds (p95)

**Manual rollback:**
```bash
./scripts/rollback.sh <version>
```

Rollback completes in < 5 minutes.

## Configuration

```yaml
deployment:
  schedule: "47 3 * * *"  # 03:47 UTC daily
  timeout: 15m
  health_check_interval: 30s
  rollback_threshold: 3
```

## Related Documents
- [Incident #2847 Postmortem](incidents/2024-q3-incident-2847.md)
- [Database Backup Schedule](infrastructure/backup-schedule.md)
- [Monitoring & Alerts](operations/monitoring.md)

## Contact
- **Deployment Team**: deploy@company.com
- **On-call**: Check PagerDuty
- **Slack**: #deployments

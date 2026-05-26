# Incident #2847 - Deployment Conflict with Database Backup

**Date**: September 15, 2024  
**Severity**: High (15-minute outage)  
**Status**: Resolved  
**Impact**: 15,000 users affected

## Summary
Automated deployment at 04:00 UTC conflicted with database backup window, causing connection pool exhaustion and service degradation.

## Timeline (All times UTC)

### 04:00:00 - Incident Start
- Automated deployment initiated
- Database backup job started simultaneously
- Connection pool begins filling up

### 04:03:15 - First Alerts
- PagerDuty alert: High database connection count
- Monitoring: Response time p95 > 5 seconds
- Error rate spike: 2% → 15%

### 04:05:30 - Service Degradation
- Connection pool exhausted (max 100 connections)
- Users experiencing timeouts
- Health checks failing

### 04:08:00 - Incident Declared
- On-call engineer paged
- Deployment paused at 60% completion
- Investigation started

### 04:12:00 - Root Cause Identified
- Deployment + backup = 150 concurrent connections needed
- Max pool size = 100 connections
- Both processes competing for limited resources

### 04:15:00 - Resolution
- Manually completed backup (was 80% done)
- Resumed deployment
- Connection pool freed up
- Services recovered

### 04:20:00 - Incident Closed
- All services healthy
- Error rate back to normal (< 0.1%)
- Post-incident monitoring active

## Root Cause

**Primary**: Deployment schedule (04:00 UTC) overlapped with database backup window (04:00-04:15 UTC)

**Contributing Factors**:
1. No validation of deployment schedule against maintenance windows
2. Connection pool size not tuned for peak loads
3. Backup job priority not configured (could have been deferred)

## Impact

- **Users Affected**: ~15,000 (10% of active users at that hour)
- **Duration**: 15 minutes
- **Revenue Impact**: $2,400 (estimated)
- **SLA Impact**: Monthly SLA still met (99.95% vs 99.9% target)

## Resolution

### Immediate Actions (Completed)
1. ✅ Changed deployment time to **03:47 UTC** (47 minutes before backup)
2. ✅ Increased connection pool to 150 connections
3. ✅ Added deployment schedule validation in CI/CD pipeline

### Short-term Actions (Completed)
1. ✅ Implemented backup job deferral logic (waits if deployment in progress)
2. ✅ Added monitoring for concurrent resource usage
3. ✅ Updated runbooks with conflict scenarios

### Long-term Actions (In Progress)
1. 🔄 Migrate to read replicas for backup jobs (Q4 2024)
2. 🔄 Implement dynamic connection pool sizing (Q1 2025)
3. ✅ Quarterly review of all scheduled maintenance windows

## Lessons Learned

### What Went Well
- Quick detection (3 minutes from start)
- Team responded promptly
- Root cause identified quickly
- Clean recovery with no data loss

### What Could Be Improved
- **Prevention**: Should have validated deployment schedule against all maintenance windows
- **Detection**: Need alerts for "upcoming schedule conflicts"
- **Documentation**: Maintenance window calendar not easily accessible
- **Testing**: Never tested deployment under backup load

## Action Items

| Action | Owner | Deadline | Status |
|--------|-------|----------|--------|
| Update deployment schedule | DevOps | Sep 16 | ✅ Done |
| Increase connection pool | DBA | Sep 16 | ✅ Done |
| Add schedule validation | Platform | Sep 20 | ✅ Done |
| Implement backup deferral | Backend | Sep 25 | ✅ Done |
| Migrate to read replicas | Infra | Dec 31 | 🔄 In Progress |
| Quarterly window review | Ops | Ongoing | ✅ Scheduled |

## Related Documents
- [Deployment Process](deployment-process.md)
- [Database Backup Schedule](infrastructure/backup-schedule.md)
- [Post-Incident Review Recording](https://drive.company.com/incident-2847)

## References
- Incident Slack Thread: #incidents (Sep 15, 2024)
- PagerDuty Incident: PD-2847
- Monitoring Dashboard: grafana.company.com/incident-2847

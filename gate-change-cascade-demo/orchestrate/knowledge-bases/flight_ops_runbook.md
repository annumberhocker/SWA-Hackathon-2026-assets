# Flight Operations Runbook — GCC-2024 Rev 1.0
## Gate Change Cascade Demo — Anomaly Response Procedures

---

## §1 — Gate Wait Anomalies

A gate wait anomaly occurs when the average time passengers or aircraft spend waiting at a gate exceeds the ARIMA upper confidence bound by more than 95%.

### Thresholds

| Condition | Severity |
|---|---|
| gate_wait > 30 min above baseline | CRITICAL |
| gate_wait 15–30 min above baseline | HIGH |
| gate_wait 8–15 min above baseline | MEDIUM |
| gate_wait < 8 min above baseline | LOW |

### §1 Option A — Immediate Gate Reassignment (CRITICAL / HIGH)
**Trigger:** ARIMA anomaly score >=  0.7  
**Action:**
1. Contact Hub Operations Center immediately (ORD: +1-312-555-0100 / DFW: +1-972-555-0200)
2. Request alternate gate assignment from Gate Control
3. Notify ground crew lead via radio channel ops-3
4. Update FIDS display; push passenger notification via app
5. If delay > 30 min, trigger passenger rebooking eligibility
6. Open ServiceNow incident (urgency 1) and assign to Gate Operations team

**Expected resolution:** 20–40 minutes  
**Escalate to Option A+:** If no alternate gate available within 15 min, escalate to Airport Ops Director

---

### §1 Option B — Standby Monitoring with Ground Crew Dispatch (MEDIUM)
**Trigger:** ARIMA anomaly score 0.5–0.7  
**Action:**
1. Dispatch ground crew supervisor to gate for visual inspection
2. Check jet bridge status in AIMS system
3. Monitor FIDS for delay cascade on connecting flights
4. If gate_wait exceeds HIGH threshold within 15 min, escalate to Option A

**Expected resolution:** 15–25 minutes

---

### §1 Option C — Monitor and Log (LOW)
**Trigger:** ARIMA anomaly score < 0.5  
**Action:**
1. Log event in flight ops journal
2. No immediate crew dispatch required
3. Re-evaluate if anomaly persists for 3+ consecutive windows

---

## §2 — Departure Delay Anomalies

A departure delay anomaly occurs when average departure delay deviates beyond the ARIMA confidence band, indicating a systemic delay pattern rather than normal operational scatter.

### Delay Buckets

| Departure Delay | DOT Classification | Reporting Required |
|---|---|---|
| < 15 min | On Time | No |
| 15–30 min | Minor Delay | Log only |
| 30–60 min | Moderate Delay | Notify passenger services |
| > 60 min | Significant Delay | Full escalation + DOT report |

### §2 Option A — Full Escalation (CRITICAL / HIGH)
**Trigger:** departure_delay value > 30 min AND anomaly_score >=  0.7  
**Action:**
1. Escalate to Duty Manager and inform Station Manager
2. Initiate passenger communication (app push + gate announcement)
3. Activate passenger rebooking protocol if delay > 60 min
4. Check crew rest compliance — if delay pushes crew over duty time limit, initiate crew swap
5. Coordinate with ATC for revised slot time
6. Open ServiceNow P1 incident; assign to Dispatch Operations

**Expected resolution:** 30–90 minutes  
**Regulatory note:** FAA tarmac delay rule (3h domestic / 4h international) must be monitored

---

### §2 Option B — Proactive Notification (MEDIUM)
**Trigger:** departure_delay 15–30 min AND anomaly_score 0.5–0.7  
**Action:**
1. Push delay notification to passengers via app
2. Update gate agent on revised estimated departure
3. Coordinate gate hold with jetway crew
4. Monitor connecting passengers — flag minimum connection time risks

---

### §2 Option C — Monitor (LOW)
**Trigger:** anomaly_score < 0.5  
**Action:**
1. Log in daily ops report
2. Gate agent monitors and reports if delay increases

---

## §3 — Turnaround Time Anomalies

A turnaround anomaly occurs when average aircraft turnaround time exceeds the ARIMA forecast, indicating ground operations are running longer than expected.

### Turnaround Root Cause Checklist

| Root Cause | First Check |
|---|---|
| Fueling delay | Contact fuel vendor — check truck availability |
| Catering delay | Contact catering coordinator |
| Cleaning delay | Check cleaning crew headcount vs. aircraft size |
| Baggage loading delay | Check belt loader availability at gate |
| Late inbound aircraft | Downstream impact — check block-out time |
| Maintenance hold | Coordinate with Line Maintenance (see §4) |

### §3 Option A — Ground Operations Escalation (CRITICAL / HIGH)
**Trigger:** turnaround_time value > 60 min OR anomaly_score >=  0.7  
**Action:**
1. Dispatch Ramp Supervisor to gate immediately
2. Conduct root cause checklist above; address highest-impact item first
3. Request priority fueling and/or catering if vendor SLA is breached
4. If cleaning is root cause: authorize premium cleaning crew overtime
5. Update block-out estimate in AIMS; notify Crew Scheduling
6. Open ServiceNow incident (urgency 1); assign to Ground Operations

**Expected resolution:** 20–45 minutes

---

### §3 Option B — Expedited Coordination (MEDIUM)
**Trigger:** turnaround_time 15–20 min over baseline AND anomaly_score 0.5–0.7  
**Action:**
1. Contact gate coordinator; request status of each ground service
2. Prioritize fueling completion (critical path)
3. Authorize catering team to begin boarding before catering complete if items are non-essential

---

### §3 Option C — Monitor (LOW)
**Trigger:** anomaly_score < 0.5  
**Action:**
1. Log in daily ops report
2. No immediate escalation needed

---

## §4 — Fleet Reference

| Aircraft | Type | Hub | Flights | Ops Contact |
|---|---|---|---|---|
| N101AX | B737-800 | ORD | AX101 (ORD->LAX) | ORD Station Ops: +1-312-555-0110 |
| N202AX | A320neo  | ORD | AX202 (ORD->JFK) | ORD Station Ops: +1-312-555-0110 |
| N303AX | B737-MAX | DFW | AX303 (DFW->MIA) | DFW Station Ops: +1-972-555-0210 |
| N404AX | A321XLR  | DFW | AX404 (DFW->SEA) | DFW Station Ops: +1-972-555-0210 |

### Hub Operations Centers

| Hub | Phone | Slack Channel | ServiceNow Assignment Group |
|---|---|---|---|
| ORD | +1-312-555-0100 | #ops-ord-alerts | Gate Operations ORD |
| DFW | +1-972-555-0200 | #ops-dfw-alerts | Gate Operations DFW |

### Escalation Chain

```
Gate Agent
  +-- Gate Coordinator
        +-- Duty Manager / Station Manager
              +-- Hub Operations Director
                    +-- VP Flight Operations (CRITICAL only)
```

---

*Gate Change Cascade Demo — Flight Operations Runbook GCC-2024 Rev 1.0*  
*For demo purposes only. Contact information is fictional.*

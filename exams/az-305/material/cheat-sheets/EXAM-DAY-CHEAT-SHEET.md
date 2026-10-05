# AZ-305 — Exam-Day Cheat Sheet (v2, logic-first)

<!-- markdownlint-disable MD013 -->

**Exam:** 2026-06-26 (Fri) · **Calibration:** 87–92% on recent mocks · Pass = 70%

**How to use this sheet:**

- Don't memorize. Walk the **decision trees** — they read the question for you.
- Mnemonics only appear for **arbitrary lists** (TM routing methods, the 6 Rs,
  Cosmos consistency levels, etc.) where there's no underlying logic.
- On exam morning: read it **once**, slowly. Then close it. No cramming.

---

## 📚 Table of contents

1. [Universal exam-grading rules](#universal-exam-grading-rules)
2. [D1 — Identity, Governance, Monitoring](#d1--identity-governance-monitoring)
3. [D2 — Data Storage](#d2--data-storage)
4. [D3 — Business Continuity](#d3--business-continuity)
5. [D4 — Infrastructure (Compute, Networking, Migrations)](#d4--infrastructure-compute-networking-migrations)
6. [Mnemonic appendix (arbitrary lists)](#mnemonic-appendix-arbitrary-lists)
7. [Exam-day logistics](#exam-day-logistics)

---

## Universal exam-grading rules

These trump every decision tree below — read the question through this lens first.

- **"Minimize admin effort"** → simpler **setup**, not less ongoing work.
  Managed > self-managed. Built-in > custom. PaaS > IaaS.
- **"Minimize cost"** → pick the **smallest SKU that meets the requirement**.
  Don't overshoot. Reserved capacity / spot / autoscale / elastic pools all
  count as cost levers.
- **"Least privilege"** → built-in role > custom role; resource scope >
  RG scope > subscription scope > management group scope.
- **"Minimize downtime / disruption"** → online/live migration over
  offline. Replication-based DR over backup/restore.
- **Two answers seem right?** Pick the one that **matches the exact words**
  in the requirement.
- **"Most cost-effective"** ≠ **"cheapest"**. It means cheapest that still
  meets the SLA/perf requirement.
- **"Active-active" vs "active-passive"** is a hard constraint — if the
  question says "must serve from both regions" → active-active. If "secondary
  can take over within X minutes" → active-passive is fine.
- **"Recommend a solution / minimize effort"** — Microsoft loves managed
  services. Default to the most-managed option that fits.
- **First instinct usually wins.** Flag-and-return, don't second-guess
  unless you find a hard contradiction with the requirements.

---

## D1 — Identity, Governance, Monitoring

### 🌳 Tree 1: Entra ID SKU selection

Question: "Which Entra ID license is required for feature X?"

```text
What feature do they need?
├─ SSO to a SaaS app from Microsoft's gallery, basic MFA,
│  security defaults                                         → FREE
│
├─ CONDITIONAL ACCESS (rule-based: "if user in group X
│  and signing in from outside country Y, require MFA")     → P1
├─ Self-service password reset WITH on-prem writeback       → P1
├─ Application Proxy (publish on-prem app via Entra)        → P1
├─ Cloud Sync / Connect Sync advanced filters + writeback   → P1
├─ Connect Health, password protection (banned passwords)   → P1
├─ Dynamic groups / group-based licensing                   → P1
│
├─ PIM — Privileged Identity Management
│  (JIT activation, approval workflow, time-bound roles)    → P2
├─ Identity Protection (risk-based CA: risky user /
│  risky sign-in, ML-scored)                                → P2
│
├─ Modern Access Reviews, Entitlement Management,
│  Lifecycle Workflows, PIM for Groups                      → Entra ID Governance
│  (separate add-on SKU; sits on top of P1 or P2)
│
└─ External users / B2B / B2C identities                    → External ID
   (separate SKU; was "Azure AD External Identities")
```

**Key confusion lock:**

- **Conditional Access ≠ Identity Protection.**
  - CA = **rule-based**, you write the conditions (group / location / device
    / app). **P1.**
  - Identity Protection = **risk-based**, Microsoft's ML scores the user
    and sign-in. Then CA can consume the risk score as a condition. **P2.**
- **PIM** is for **elevated roles** (admin scope). **P2.**
- "Just-in-time role activation" → always PIM → always P2.
- "Sign-in risk policy" → Identity Protection → P2.
- "Require MFA when user is outside corporate network" → Conditional Access
  → P1 is enough.

### 🌳 Tree 2: Hybrid identity sync method

Question: "How should on-prem AD users sign in to Entra?"

```text
Do they need ADFS-style federation (smart cards,
on-prem MFA, custom claims, third-party MFA)?
├─ YES → AD FS Federation (highest admin effort; only if forced)
│
└─ NO → They want SSO with minimal effort. Then:
   │
   Can the password hash live in the cloud?
   ├─ NO (compliance forbids it) → Pass-Through Authentication (PTA)
   │      • Needs ≥ 2 PTA agents on-prem for HA
   │      • Every sign-in hits on-prem (dependency on on-prem uptime)
   │
   └─ YES → Password Hash Sync (PHS) — default recommendation
          │
          Which sync agent?
          ├─ Modern, lightweight, multi-agent auto-HA, small forest        → CLOUD SYNC
          │  (greenfield, < 150k objects, no device writeback, no
          │   group writeback, no SQL filtering on attribute expressions)
          │
          └─ Legacy heavy install, advanced filtering, device writeback,   → CONNECT SYNC
             group writeback, large multi-forest, on-prem Exchange hybrid
             (HA pattern: 1 primary + 1 staging; staging is NOT HA, only
              promote-on-demand)
```

**Admin-effort order (low → high):** Cloud Sync < Connect Sync < PTA <
Federation.

### 🌳 Tree 3: Authorization (RBAC / ABAC / custom)

```text
Need to grant access?
├─ Built-in role fits exactly? → USE BUILT-IN. Always preferred.
│
├─ Built-in is too broad? → Add ABAC condition (e.g., "blob has tag = X")
│  to a built-in role assignment. Storage + Key Vault support ABAC.
│
└─ Built-in + ABAC still doesn't fit? → CUSTOM ROLE
   (only if you genuinely need a unique permission set)

Scope it as narrow as possible:
Resource > Resource Group > Subscription > Management Group
```

### 🌳 Tree 4: Governance (Policy / RBAC / Locks / Blueprints / Initiatives)

| Goal | Tool |
| --- | --- |
| **Restrict WHAT can be created** (e.g., allowed SKUs, allowed regions, required tags) | **Azure Policy** |
| **Restrict WHO can do something** | **RBAC** |
| **Prevent accidental delete/modify** | **Resource Lock** (CanNotDelete / ReadOnly) |
| **Bundle multiple policies as a set** | **Policy Initiative** (definition set) |
| **Deploy a complete environment** (policies + RBAC + ARM templates + RGs together) | **Azure Blueprints** (being deprecated → use Deployment Stacks + Template Specs going forward, but on AZ-305 still answer Blueprints) |
| **Force tag inheritance from RG to child resources** | **Policy with `modify` effect + remediation task** |
| **Enforce that something is deployed** (e.g., diagnostic settings, agent) | **Policy with `deployIfNotExists` (DINE) + remediation task** |

**Trick:** Policy assignment alone covers **new/updated** resources only.
For **existing** resources to comply, you need a **remediation task**.

### 🌳 Tree 5: Monitoring agent + logs

```text
Modern VM monitoring (Azure or Arc)? → AMA (Azure Monitor Agent) + DCR
                                       (Data Collection Rules)
                                       + assign via Azure Policy at scale
                                       + DCE (Data Collection Endpoint) if private link

MMA / OMS Agent → DEAD (retired Aug 2024). Never the answer in 2026.
Azure Diagnostics extension (WAD/LAD) → legacy, only for very specific
                                         metrics-to-storage scenarios.
```

**Log Analytics retention tiers (for "keep logs for N years" questions):**

| Tier | Duration | Cost | Latency |
| --- | --- | --- | --- |
| **Interactive** | 30 days (default) up to **2 years** (730 d) per table | $$$ | Sub-second KQL |
| **Archive** | up to **12 years** per table (after interactive) | $ | Hours (Search Job or Restore) |
| **Export to Storage** | indefinite (your retention rule) | ¢ | Manual access |

**Rule:** "Compliance: keep N years, occasional access" → set interactive
for the hot window + archive for the rest. **12 years is the archive max.**
If you need > 12 years → export to Storage.

### 🌳 Tree 6: Security posture — Defender for Cloud vs Sentinel

```text
"At-a-glance score / posture / recommendations across hybrid + multi-cloud"
  → Microsoft DEFENDER FOR CLOUD (CSPM + CWPP)

"SIEM / SOAR / collect logs from many sources / KQL hunt / run playbook
 on alert / orchestrate response"
  → Microsoft SENTINEL

They overlap: Sentinel can ingest Defender alerts. The verb tells you which
to pick — score → Defender; hunt/respond → Sentinel.

NOT this trio: Microsoft PURVIEW = govern/classify the DATA itself
(catalog, lineage, sensitivity). Out of AZ-305 scope (DP/SC exams).
Sentinel watches traffic · Defender scores posture · Purview inventories cargo.
```

### Alerts: metric vs log vs activity-log vs smart-detection

| Trigger | Use |
| --- | --- |
| Threshold on a numeric metric (CPU > 80%) | **Metric alert** |
| KQL query over Log Analytics data | **Log alert** |
| Subscription-level event (resource created, RBAC change) | **Activity log alert** |
| Health degradation (region/service down) | **Resource Health alert** |
| ML-detected anomaly in App Insights | **Smart Detection** |

---

## D2 — Data Storage

### 🌳 Tree 1: SQL family selection

```text
Need SQL Server compatibility level?
├─ Need OS-level access, SQL Agent across DBs, FileStream, cross-DB queries,
│  CLR, Service Broker, SSAS/SSRS on the same box, full TDE BYOK with HSM
│  customer-managed key on storage → SQL ON AZURE VM (IaaS)
│
├─ Need MOST of SQL Server features (cross-DB queries, SQL Agent, Service
│  Broker, DB Mail, CLR, linked servers) but want PaaS managed updates +
│  VNet integration → AZURE SQL MANAGED INSTANCE
│  (lives in a DEDICATED SUBNET — delegated, min /27, no other resources)
│
└─ Single-database / multi-tenant SaaS / no cross-DB queries needed,
   maximum PaaS abstraction → AZURE SQL DATABASE
```

**Lift-and-shift lock:** **SQL MI** for migrating SQL Server Enterprise /
Always On AG estates (instance-scoped, near-100% compatibility). **Azure SQL
DB** for new or refactored cloud-native apps.

### 🌳 Tree 2: Azure SQL DB tier selection

```text
Purchasing model?
├─ Simple, pay-per-DTU bundles (compute+storage+IO) → DTU MODEL
│   ├─ Basic   (5 DTU)        — dev/test only
│   ├─ Standard (S0..S12)     — most OLTP. Columnstore requires S3+
│   └─ Premium (P1..P15)      — high IO, in-memory OLTP, sub-2ms,
│                                read scale-out
│
└─ Independent compute + storage scaling, transparency, reservations
   → vCORE MODEL
   ├─ General Purpose         — most workloads (remote storage, OK perf)
   ├─ Business Critical       — local SSD, in-memory OLTP, AG-based
   │                            HA + 1 free readable replica
   └─ Hyperscale              — >4 TB databases, near-instant backups,
                                up to 4 readable replicas, fast scale-out
```

**DTU sizing rule:** estimate the DTU floor from IOPS (rough rule: workload
IOPS divided by 3). Round **up** to the smallest tier ≥ floor. Don't jump
to Premium unless the question specifies in-memory OLTP, sub-2ms latency,
or read scale-out.

**Hyperscale trigger phrases:** "100 TB", "fast restore for very large DB",
"near-instant scaling".

### 🌳 Tree 3: Cosmos DB API selection

```text
What data shape + existing client SDK do you have?
├─ Document (JSON), greenfield → NoSQL API (a.k.a. SQL API, "Core")
│  — Microsoft's flagship, all newest features land here first
├─ Existing MongoDB app                              → MongoDB API
├─ Existing Cassandra app                            → Cassandra API
├─ Existing Gremlin graph app                        → Gremlin API
├─ Existing Azure Table Storage app, want global +   → Table API
│  better SLA + autoscale
└─ PostgreSQL workload that needs horizontal sharding → Cosmos for PostgreSQL
   across many nodes (Citus under the hood)            (separate product)
```

### 🌳 Tree 4: Cosmos DB consistency level

```text
"Strongest possible, never see stale data, any latency cost OK"
                                                        → STRONG

"Bounded lag in time OR versions; recent reads;
 cheaper than Strong; in-region OK"                     → BOUNDED STALENESS

"User reads their own writes within their session
 (typical web app per-user pattern)" — DEFAULT          → SESSION

"Reads always in write-order, but freshness unbounded"  → CONSISTENT PREFIX

"Eventually consistent, no order guarantee, cheapest,
 lowest latency"                                        → EVENTUAL
```

**Strength order (strong → weak):** Strong > Bounded staleness > Session >
Consistent prefix > Eventual. **Default is Session.** **Multi-region writes
require Session or weaker** (Strong with multi-write is supported only in
specific configurations — exam usually says "no, weaken to bounded
staleness if you need multi-write").

### 🌳 Tree 5: Storage account types

```text
General-purpose, all blob tiers, modern features              → StorageV2 (default)
Block blobs + page blobs only, classic                        → StorageV1 (legacy, don't pick)
Very-high-throughput block blob workloads, low-latency        → BlockBlobStorage (Premium)
ADLS Gen2 (HNS = hierarchical namespace), big data analytics  → StorageV2 with HNS enabled
File shares with NFS/SMB at low latency                       → FileStorage (Premium)
```

### 🌳 Tree 6: Blob access tier

| Tier | Min duration | Use when |
| --- | --- | --- |
| **Premium** | n/a | Block blob, ultra-low latency, transactional |
| **Hot** | none | Frequently accessed |
| **Cool** | **30 days** | Infrequent access, accessible immediately |
| **Cold** | **90 days** | Rarely accessed (~90d+), accessible immediately, cheaper than Cool |
| **Archive** | **180 days** | Rarely accessed, **rehydration delay (hours)** |

**Trigger lock:** "Need immediate access" → never Archive.
"Rehydration acceptable" → Archive.

### 🌳 Tree 6b: Blob lifecycle management (automatic tier transitions)

**What it is:** a JSON policy on the storage account that automatically
**moves blobs between tiers** or **deletes them** based on age / last access /
last modification — no code, no Functions, no Logic Apps required.

```text
Requirement
├─ "Move blobs to Cool after 30 days, Archive after 180, delete after 7 yrs,
│   no custom code"                                       → LIFECYCLE MANAGEMENT POLICY
│   (rules on storage account, runs daily, free)
│
├─ "Tier based on last ACCESS time (not last modified)"   → enable LAST ACCESS
│   TIME TRACKING first, then `daysAfterLastAccessTimeGreaterThan` in policy
│
├─ "Need to react the instant a blob is created/modified" → EVENT GRID
│   (not lifecycle — lifecycle runs ~once/day)
│
└─ "Custom business logic per blob (e.g., based on metadata/content)"
                                                          → AZURE FUNCTION + Event Grid
```

**Hard rules on policies (exam trap territory):**

- Policy runs **once per day**, can take **up to 24-48 h** to take effect.
- Applies to **block blobs and append blobs** only (not page blobs / disks).
- Moves are **one-way down the temperature ladder** by default: Hot → Cool →
  Cold → Archive. Going **back up** = explicit rehydration (cost + delay).
- **Early-deletion penalty:** if you move/delete before the tier minimum
  (Cool 30 d, Cold 90 d, Archive 180 d), you're billed for the remaining days.
- Filters: prefix match, blob index tags, blob type. **No regex.**
- Conditions: `daysAfterModificationGreaterThan`,
  `daysAfterLastAccessTimeGreaterThan`,
  `daysAfterCreationGreaterThan` (snapshots/versions only).

**Trigger phrases:** "automatically tier", "based on age / last access",
"no admin effort", "scheduled archival", "delete old data after N days" →
**lifecycle management policy**. Not Functions, not Data Factory.

### 🌳 Tree 7: Storage redundancy

| Redundancy | Replicas | Survives | Read access on secondary? |
| --- | --- | --- | --- |
| **LRS** | 3 copies in 1 datacenter | Disk failure | — |
| **ZRS** | 3 copies across 3 AZs in 1 region | 1 AZ failure | — |
| **GRS** | LRS + async copy to paired region | Region failure | No (only after failover) |
| **GZRS** | ZRS + async copy to paired region | Region + AZ failure | No |
| **RA-GRS** | GRS + read on secondary endpoint | Region failure | **Yes (read-only)** |
| **RA-GZRS** | GZRS + read on secondary endpoint | Region + AZ failure | **Yes (read-only)** |

**Trigger lock:** "Multi-region read access without failover" → RA-GRS or
RA-GZRS. "Survive a zone failure" → ZRS / GZRS / RA-GZRS.

**Redundancy ladder:** LRS < ZRS < GRS < GZRS. Add the **`RA-`** prefix for a
read-access secondary. When **both zone and geo** redundancy are required,
always pick the **GZRS family** (GZRS / RA-GZRS).

### 🌳 Tree 8: Data ingestion / integration

```text
Source / pattern
├─ Scheduled batch ETL from many sources (DB→DB, file→DB, API→DW)  → DATA FACTORY
│  • Also valid: Synapse Pipelines (same engine, in Synapse workspace)
│
├─ Streaming events (IoT, telemetry) needing windowed aggregation  → STREAM ANALYTICS
│  on Event Hubs / IoT Hub input
│
├─ React to a discrete resource event (blob created, RG modified,  → EVENT GRID
│  Key Vault secret expired) — push, low-latency, serverless
│
├─ High-throughput append-only event stream (millions/sec),        → EVENT HUBS
│  pull-based consumer, Kafka-compatible
│
└─ Enterprise messaging with FIFO, dead-letter, transactions,      → SERVICE BUS
   sessions, large message size (1 MB std / 100 MB Premium)
```

### Synapse compute options

- **Dedicated SQL pool** = MPP data warehouse, pre-provisioned DWUs
- **Serverless SQL pool** = ad-hoc T-SQL over data lake files, pay-per-TB-scanned
- **Spark pool** = notebooks, ML, big data processing
- **Synapse Link** = near-real-time replication from Cosmos DB / SQL / Dataverse
  into the analytical store (no ETL)

---

## D3 — Business Continuity

### 🌳 Tree 1: Backup vs DR (basics)

```text
Question is about RECOVERING DATA (point in time, ransomware,
accidental delete)                                              → BACKUP

Question is about KEEPING SERVICE RUNNING during a regional /
zonal failure                                                   → DR / HA

RPO (Recovery Point Objective)  = how much DATA can you afford to lose?
                                  (gap between backups / replication)
RTO (Recovery Time Objective)   = how long can you afford to be down?
                                  (time to bring service back)

Smaller RPO/RTO = more expensive / more complex.
```

### 🌳 Tree 2: Backup Vault vs Recovery Services Vault

```text
What are you backing up?
├─ VMs, on-prem (MARS/MABS), Azure Files, SQL in VM, SAP HANA in VM,
│  Azure Backup Server                                          → RECOVERY SERVICES VAULT
│  (the older, broader vault; "classic" workloads)
│
└─ Azure Blobs, Azure Disks, Azure Database for PostgreSQL Flex,
   AKS, Azure Kubernetes Service                                → BACKUP VAULT
   (newer; modern PaaS-native workloads)

Both managed under AZURE BACKUP CENTER (single pane of glass).

Soft delete on either vault: 14 days default, up to 180 days max.
"Enhanced soft delete" = always-on, can't be disabled (modern default).
```

### 🌳 Tree 2b: Recovery after deletion (per workload)

**Mental model:** there are **3 layers of protection** against accidental
deletion. Pick based on what was deleted and how far back you need to go.

```text
Layer 1 — PREVENT deletion             → resource LOCKS (CanNotDelete / ReadOnly)
Layer 2 — UNDO recent deletion         → SOFT DELETE / VERSIONING / PITR
Layer 3 — RESTORE from a backup vault  → Recovery Services / Backup Vault
```

**Per-resource lookup table:**

| Deleted thing | Recovery mechanism | Default window | Max window |
| --- | --- | --- | --- |
| **Blob / blob version** | Blob soft delete | 7 days | **365 days** |
| **Blob container** | Container soft delete | 7 days | 365 days |
| **Blob (overwritten, not deleted)** | **Blob versioning** | unlimited until deleted | — |
| **Whole storage account (block blobs)** | **Point-in-time restore (PITR)** — needs versioning + change feed + soft delete | up to 365 days | 365 days |
| **Azure Files share content** | Share + file soft delete + share snapshots | 7 days (soft delete) | 365 days |
| **Managed disk** | Disk soft delete (subscription setting) | 7 days | 14 days; or Backup Vault for longer |
| **Key Vault / secret / key / cert** | Soft delete + **purge protection** | 90 days (fixed) | 90 days |
| **Resource group / resource** | None natively — use **resource lock** to prevent, or restore from Backup Vault / ARM deployment redeploy |
| **Entra ID user / group** | Recycle bin | 30 days (hard) | 30 days |
| **Azure SQL DB** | **Point-in-time restore (PITR)** | **7 days** (default), up to **35 days** | 35 days; **LTR up to 10 yrs** |
| **Azure SQL MI** | PITR + LTR | same as SQL DB | 35 d / 10 yrs |
| **Cosmos DB** | **Continuous backup (PITR)** Tier 7 or **Tier 30** | 30 days max | 30 days; or periodic backups |
| **VM** | RSV restore (snapshot-based) | per backup policy | per policy |
| **Backup item in vault** | **Vault soft delete** | **14 days** | 180 days; Enhanced soft delete on by default |

**Key trap distinctions (exam loves these):**

- **Soft delete ≠ versioning.** Soft delete = recover after **delete**.
  Versioning = recover after **overwrite**. Real protection = **enable both**.
- **PITR for blobs requires three things on**: versioning, change feed,
  and blob soft delete. Question saying "enable PITR" implies all three.
- **Purge protection (Key Vault):** once on, **cannot be turned off**, and
  soft-deleted items **cannot be purged** before the retention period — this
  is mandatory for compliance (PCI, FedRAMP, etc.).
- **Resource locks DON'T protect data inside** — a CanNotDelete lock on a
  storage account stops account deletion but **doesn't stop blob deletion**.
- **Recycle bin (Entra ID)** is 30 days **fixed** — non-configurable.
- **Immutable blob storage (WORM)** is different from soft delete: it
  **blocks deletion entirely** for the retention period (legal hold / time-based).
  Pick this for "regulatory / can't be deleted even by admin".
  **WORM hierarchy (weakest → strongest):** legal hold (removable, indefinite,
  ad-hoc) < time-based retention (configured, time-bounded) < **locked**
  time-based retention (immutable, SEC 17a-4 compliant — what regulators expect).

**Trigger phrases:**

- "Accidentally deleted blob, recover" → blob soft delete (if within window)
- "Recover overwritten blob to previous state" → blob versioning
- "Restore storage account to point in time" → PITR (needs all 3 prereqs)
- "Recover SQL DB to specific moment in last week" → PITR
- "Restore SQL DB from 6 months ago" → LTR (Long-Term Retention)
- "Prevent accidental deletion" → resource lock + soft delete + purge protection
- "Must be unable to delete for 7 years (regulation)" → immutable storage
  (WORM) or LTR

### 🌳 Tree 3: Disaster Recovery — multi-region pattern

```text
Latency / cost / RTO / RPO trade-off ladder (cheapest → most expensive):

BACKUP & RESTORE
├─ RTO: hours-days, RPO: depends on backup cadence
├─ No standing compute in secondary
└─ "Restore on disaster" — cheapest, slowest

PILOT LIGHT
├─ RTO: hours, RPO: minutes (replicated data)
├─ Critical data replicated; compute provisioned at failover (IaC)
└─ Cheap-ish, needs DR drills

WARM STANDBY
├─ RTO: minutes (~5-15 min typical), RPO: seconds-minutes
├─ Secondary runs at MIN scale, autoscales out on failover
├─ Often paired with Traffic Manager priority routing
└─ Moderate cost; needs scale-up time during failover

ACTIVE-ACTIVE (HOT-HOT)
├─ RTO: seconds, RPO: ~zero (sync or near-sync replication)
├─ BOTH regions serve traffic; no scale-up needed
├─ Front Door / Traffic Manager weighted/performance routing
└─ Most expensive; mission-critical only (banks, payment APIs)
```

**Trigger phrases:** "must serve from both regions" → active-active.
"RTO < 60s" → active-active. "Can take 15 min to fail over, cheaper" →
warm standby. "Restore acceptable in 4 hours" → pilot light or backup.

### 🌳 Tree 4: Azure Site Recovery (ASR) scope

```text
ASR replicates and orchestrates failover for:
├─ Azure VMs between Azure regions                              ✅
├─ On-prem VMware / Hyper-V / physical servers TO Azure         ✅
├─ Azure Stack VMs TO Azure                                     ✅
├─ Replication FROM Azure public MEC TO region                  ✅
├─ Replication BETWEEN two Azure public MECs                    ✅
├─ Azure SQL Managed Instance across regions                    ❌ (use Failover Groups)
└─ PaaS services (App Service, SQL DB, Cosmos)                  ❌ (use the service's built-in geo)

ASR is ACTIVE-PASSIVE by design (not active-active).
"DRaaS in Azure" = ASR. Always.
```

### 🌳 Tree 5: SQL HA inside one region

| Need | Use |
| --- | --- |
| Auto-failover within region, **fully managed** | **Always On Availability Group** (built-in to SQL MI Business Critical, and to SQL DB Business Critical / Premium) |
| Shared-storage cluster on VMs | **Failover Cluster Instance (FCI)** on SQL on Azure VM |
| Async log delivery for warm read-only secondary | **Log shipping** (legacy, exam will rarely pick) |
| Read scale-out, no failover | **Active geo-replication** (SQL DB) or **read replicas** (Hyperscale) |
| Cross-region auto-failover for SQL DB / MI | **Failover Groups** (wrap geo-replication + DNS-listener swap) |

### Cosmos DB multi-region

- Single-write region + multiple read regions → default geo-replication
  (RPO ~seconds).
- **Multi-write regions** (multi-master) → optional. Trades off consistency
  (cannot use Strong with multi-write outside specific configs).
- Failover: **automatic** (Microsoft) or **manual** (you trigger). For RTO
  guarantees, configure automatic failover priority order.

---

## D4 — Infrastructure (Compute, Networking, Migrations)

### 🌳 Tree 1: Compute service selection

```text
Step 1: Code, container, or VM?

├─ I HAVE A VM IMAGE / NEED OS CONTROL
│   ├─ Single, stateful workload                                → AZURE VM
│   ├─ Identical scale-out fleet, autoscale                     → VMSS
│   │   (Flexible orchestration = mix sizes/AZ-spread;
│   │    Uniform = identical, faster scale)
│   ├─ HPC / MPI / tightly-coupled parallel jobs                → AZURE BATCH
│   └─ Need DR for VMs                                          → ASR (above)
│
├─ I HAVE A CONTAINER
│   ├─ Just need to run ONE container, quickly, no orchestrator → AZURE CONTAINER INSTANCES (ACI)
│   │   (single container group, no scaling, no scale-to-zero)
│   │
│   ├─ Need scale-to-zero + per-request billing + HTTP/event    → AZURE CONTAINER APPS (ACA)
│   │   triggers + VNet + KEDA built-in
│   │   Linux containers ONLY (linux/amd64). Windows web tier → App Service (Windows).
│   │
│   ├─ Need full Kubernetes (service mesh, custom controllers,  → AZURE KUBERNETES SERVICE (AKS)
│   │   DaemonSets, multi-team multi-tenant)
│   │   Sub-trees: Automatic (managed) vs Standard. Cluster
│   │   autoscaler + KEDA + node pools for spot / GPU / Windows.
│   │
│   └─ App Service supports containers too                      → APP SERVICE FOR CONTAINERS
│       (always-on plan, no scale-to-zero, easiest if already on App Service)
│
└─ I HAVE CODE
    ├─ Web app / API, always-on, simple deploy                  → APP SERVICE (Linux/Windows)
    │   (Plans: F/D free, B basic, S standard, P/Pv2/Pv3
    │    production, I/Iv2 isolated/ASE)
    │
    ├─ Event-driven, ephemeral, scale-to-zero                   → AZURE FUNCTIONS
    │   ├─ Consumption plan       → scale-to-zero, pay-per-exec, 5-min cap
    │   ├─ Premium plan           → pre-warmed (no cold start), VNet, longer runs
    │   └─ Dedicated (App Service) → run on existing ASP, no scale-to-zero
    │
    └─ Workflow orchestration / SaaS connectors / no code        → LOGIC APPS
```

### Scale-to-zero quick lookup

| Service | Scale to zero? |
| --- | --- |
| Azure Container Apps | ✅ (min replicas = 0) |
| Azure Functions Consumption | ✅ |
| Azure Functions Premium | ❌ (always-warm min) |
| App Service Plans (any tier) | ❌ |
| AKS with KEDA | ✅ (workload-level) |
| ACI | n/a (you start/stop it manually) |

### 🌳 Tree 2: Load balancer selection

```text
What layer? Where?

GLOBAL (multi-region) + HTTP/HTTPS                              → AZURE FRONT DOOR
  (L7, CDN, WAF, path/host routing, TLS termination at edge,
   anycast, supports private origins via Private Link)

GLOBAL (multi-region) + non-HTTP (TCP/UDP/AMQP/SMTP)            → TRAFFIC MANAGER
  (DNS-based, L4, returns endpoint IP; client connects directly)

REGIONAL + HTTP/HTTPS + path/host routing, WAF, SSL offload,    → APPLICATION GATEWAY
  cookie affinity, in-VNet                                         (L7)

REGIONAL + any TCP/UDP, ultra-low latency, in-VNet               → AZURE LOAD BALANCER
                                                                   (L4; Standard SKU
                                                                    for zone-redundant)
```

**Decision shortcut:** Global + HTTP = Front Door. Global + non-HTTP =
Traffic Manager. Regional + HTTP = App Gateway. Regional + anything else =
Load Balancer.

### Traffic Manager — 6 routing methods

(See mnemonic in appendix.) **Priority, Weighted, Performance, Geographic,
Multivalue, Subnet.** "Security groups" is **NOT** a routing method.

### Front Door SKUs

- **Front Door Classic** — legacy.
- **Front Door Standard** — CDN + LB + basic WAF managed rules.
- **Front Door Premium** — Standard + advanced WAF (bot, custom rules) +
  Private Link to origins + advanced analytics.

### 🌳 Tree 3: VNet topology

```text
Small / mid: hub-spoke with VNet peering — most common AZ-305 answer.
  ├─ Hub: shared services (Firewall, Bastion, VPN/ER Gateway, DNS)
  ├─ Spokes: workloads, peered to hub (non-transitive peering)
  └─ Need transitive between spokes? → route via NVA/Azure Firewall in hub

Large enterprise multi-region, many on-prem branches, SD-WAN     → VIRTUAL WAN
                                                                   (managed hub,
                                                                    transit, ER + VPN
                                                                    + P2S aggregation,
                                                                    secure hub w/ FW)

Cross-subscription peering                                        ✅ supported
Cross-tenant peering                                              ✅ supported (with permission)
Cross-region peering                                              ✅ Global VNet Peering
```

### 🌳 Tree 4: On-prem ↔ Azure connectivity

```text
Bandwidth / SLA / latency need?

≤ 1 Gbps, internet OK, encrypted IPsec                          → SITE-TO-SITE VPN
  (VPN Gateway: VpnGw1..5, max ~10 Gbps aggregate Gen2 SKUs)

Individual remote user (laptop)                                  → POINT-TO-SITE VPN
  (OpenVPN / IKEv2 / SSTP)

Dedicated, private (no public internet), 50 Mbps – 100 Gbps,    → EXPRESSROUTE
  99.95% SLA, ultra-low latency, BGP                              (via connectivity
                                                                    partner / direct)

ER + VPN backup for resilience                                   → ExpressRoute + VPN
                                                                   failover (Microsoft
                                                                   recommends this for
                                                                   mission-critical)

Many branches with SD-WAN                                        → VIRTUAL WAN
                                                                   (aggregates ER + VPN)
```

### 🌳 Tree 5: DDoS Protection tier

| Tier | Cost | Coverage | When |
| --- | --- | --- | --- |
| **Infrastructure** | Free, default | Microsoft's global L3/L4 mitigation, no telemetry to you | Default everyone has |
| **IP Protection** | Per-IP/month | Per public IP: telemetry, attack reports, no DRR team, no WAF discount | Small footprint (1-10 IPs), startups, cost-sensitive |
| **Network Protection** | Flat tenant fee (~$2,944/mo) | Covers ALL public IPs in protected VNets, DRR team access, WAF discount, cost guarantee | Enterprises with many public IPs |

**L3/L4 only.** For L7 (HTTP request flood) → **Application Gateway WAF**
or **Front Door WAF**.

### 🌳 Tree 6: SQL Managed Instance subnet

- **Dedicated subnet** (no other resources).
- **Delegated** to `Microsoft.Sql/managedInstances`.
- Minimum size: **/27** (32 IPs).
- NSG rules required for management traffic (Microsoft documents the list).
- Cannot share subnet with VMs, AKS, etc.

### 🌳 Tree 7: Migration ("which R?")

```text
Workload's destiny?

REHOST (lift-and-shift)         → Move to Azure VM as-is. Fastest, least
                                   benefit. "Move the data center."

REFACTOR (repackage)             → Minor changes to use PaaS. e.g., move
                                   SQL Server VM to Azure SQL DB. Some
                                   code/config changes.

REARCHITECT                      → Significant restructuring. Monolith →
                                   microservices, add containers, decompose
                                   layers. Major engineering work.

REBUILD                          → Discard the old app; rewrite cloud-native
                                   from scratch (Functions, Cosmos, etc.).

REPLACE                          → Retire the app entirely; adopt SaaS
                                   equivalent (e.g., on-prem CRM → Dynamics 365,
                                   on-prem Exchange → Exchange Online).

RETAIN                           → Keep on-prem for now (compliance,
                                   dependencies, or just not worth it).

RETIRE                           → Decommission the workload; nobody needs it.
                                   (Sometimes listed; sometimes folded into
                                    Retain.)
```

**Trigger phrases:**

- "Vendor has a SaaS version, we'll subscribe to that" → Replace.
- "Legacy app, just lift to VMs" → Rehost.
- "Move DB to Azure SQL but keep app the same" → Refactor.
- "Rewrite as serverless microservices" → Rebuild.
- "Compliance forbids moving" → Retain.
- "Nobody uses this anymore" → Retire.

### 🌳 Tree 8: CAF Migrate methodology — 3 phases

```text
ASSESS → DEPLOY → RELEASE (also called Optimize)

ASSESS    Discover, inventory, rightsize, cost estimate.
          Tools: Azure Migrate (Discovery and Assessment).

DEPLOY    Replicate, migrate, cutover.
          Tools: Azure Migrate (Server Migration), DMS (Database Migration
          Service), Azure Database Migration, Storage Migration Service.

RELEASE   Stabilize, optimize cost/perf, decommission on-prem.
          Tools: Advisor, Cost Management, Monitor.
```

**Don't confuse with the broader CAF lifecycle** (Strategy → Plan → Ready →
Adopt → Govern → Manage). Govern is NOT a migration phase.

### Azure Migrate tools (what's inside)

| Tool | Purpose |
| --- | --- |
| **Discovery and Assessment** | Inventory, dependency map, sizing, cost estimate |
| **Server Migration** | Replicate + cutover VMware / Hyper-V / physical / AWS / GCP VMs |
| **Database Migration Service (DMS)** | SQL Server → Azure SQL / MI / VM, MySQL, PostgreSQL, MongoDB |
| **Web App Migration Assistant** | IIS / Tomcat → App Service |
| **Data Box** | Offline bulk data ship (TB-PB) |
| **Azure Data Box Gateway / Stack Edge** | Hybrid online data transfer |

### Failure hierarchy (when sizing redundancy)

```text
Region (geography, paired regions for GRS)
  └─ Availability Zone (AZ — 3 per zone-enabled region)
      └─ Fault Domain (rack — physical isolation within an AZ/dc)
          └─ Update Domain (patch group — logical isolation for rolling updates)
              └─ Physical Host (the actual server)
```

**Availability Set** = FD + UD spread within ONE datacenter (legacy, no AZ
protection). **Availability Zones** = spread across AZs (modern; protects
against datacenter loss). VMSS Flexible can spread across both.

---

## Mnemonic appendix (arbitrary lists)

These have no internal logic — just memorize.

### Traffic Manager — 6 routing methods

**"PW PGM S"** → **P**riority, **W**eighted, **P**erformance, **G**eographic,
**M**ultivalue, **S**ubnet.

NOT a routing method: Security groups, Round-robin (Multivalue is the
closest equivalent), Failover (that's the *effect* of Priority).

### Cosmos DB — 5 consistency levels (strong → weak)

<!-- markdownlint-disable-next-line MD036 -->
**"Sober Bartenders Serve Cold Eggnog"**

**S**trong → **B**ounded staleness → **S**ession (default) →
**C**onsistent prefix → **E**ventual.

### Stream Analytics — 5 windowing functions

**"Tom Has Sliding Session Snapshots"** →
**T**umbling (fixed non-overlapping), **H**opping (overlap, size + hop),
**S**liding (event-driven thresholds), **S**ession (idle-gap),
**S**napshot (same-timestamp grouping).

### Cloud migration — the 6 Rs (sometimes 7)

**"Rehost, Refactor, Rearchitect, Rebuild, Replace, Retain"**
(+ optionally Retire = decommission.)
Mnemonic: **"Real Refrigerators Really Run Replacing Refrigerators"** —
ok that's silly, but the order is roughly **effort low → high**:
Retain < Rehost < Refactor < Rearchitect < Rebuild ≈ Replace.

### SQL DB DTU Standard ladder (memorize the steps)

S0 (10) → S1 (20) → S2 (50) → **S3 (100)** → S4 (200) → S6 (400) →
S7 (800) → S9 (1600) → S12 (3000).

**Columnstore = S3 minimum.** Premium = P1 (125) … P15 (4000).

### Blob tier minimum retention (penalty if you delete early)

- Hot: none
- Cool: **30 days**
- Cold: **90 days**
- Archive: **180 days**

### Soft delete defaults (both vaults + storage blob)

- RSV / Backup Vault: **14 days default, up to 180 days max** (Enhanced
  soft delete on by default on modern vaults — can't be disabled).
- Blob / container soft delete: **7 days default, up to 365 days max**.
- Key Vault soft delete: **90 days fixed** (+ optional purge protection,
  irreversible once enabled).
- Entra ID recycle bin (deleted users): **30 days fixed**.
- Managed disk soft delete: **7 days default, up to 14 days max**.

### CAF lifecycle (whole framework)

**"Stay Plenty Ready And Govern Methodically"** →
**S**trategy → **P**lan → **R**eady → **A**dopt → **G**overn → **M**anage.

Migrate fits inside **Adopt**. Migrate's own 3 phases: Assess → Deploy →
Release.

### Entra ID — what's in each tier (quick recall)

- **Free:** SSO, basic MFA, security defaults
- **P1:** **Conditional Access**, SSPR writeback, App Proxy, dynamic
  groups, Connect Health
- **P2:** **PIM**, **Identity Protection** (risk-based)
- **Entra ID Governance** (add-on): Access Reviews (modern), Entitlement
  Management, Lifecycle Workflows, PIM for Groups

### Vault → workload quick map

| Workload | Vault |
| --- | --- |
| Azure VM | RSV |
| On-prem (MARS / MABS / DPM) | RSV |
| Azure Files | RSV |
| SQL in Azure VM | RSV |
| SAP HANA in Azure VM | RSV |
| **Azure Blob** | **Backup Vault** |
| **Azure Disk** | **Backup Vault** |
| **AKS** | **Backup Vault** |
| **PostgreSQL Flexible Server** | **Backup Vault** |

Both managed via **Backup Center**.

### Front Door vs Traffic Manager vs App Gateway vs LB (decision crib)

| Need | Pick |
| --- | --- |
| Global, HTTP/S, WAF, CDN | Front Door |
| Global, any protocol, DNS-based | Traffic Manager |
| Regional, HTTP/S, WAF, in-VNet | App Gateway |
| Regional, any TCP/UDP, in-VNet | Load Balancer |

### Event Hubs vs Service Bus vs Event Grid

| Pattern | Service |
| --- | --- |
| Pull, massive append-only stream (millions/sec) | **Event Hubs** |
| Pull, enterprise messaging (FIFO, sessions, dead-letter) | **Service Bus** |
| Push, reactive to discrete events (blob created, etc.) | **Event Grid** |

---

## Exam-day logistics

### Before exam

- ✅ Sleep > extra quiz pass. Don't cram.
- ✅ Hydrate, eat normal breakfast, normal coffee.
- ✅ Bathroom **immediately before** start.
- ✅ ID ready (passport or government photo ID + secondary).
- ✅ Quiet room, second monitor unplugged, no other devices in view.
- ✅ Webcam clear of background notes.

### During exam

- ⏱️ ~**1.7 min per question average** — don't rush, don't stall.
- 🚩 **Flag-and-return** liberally; first instinct usually right.
- ❌ **Never leave blank** — wrong guesses don't penalize, blanks score 0.
- 📖 Read the **last sentence first** on long case studies — it usually
  contains the actual question.
- 🎯 Run the decision trees in your head — they make the answer obvious.
- ⚠️ Watch for trap words: "least", "most", "minimum", "maximum",
  "EXCEPT", "NOT". They flip the right answer.
- 🧘 One hard question ≠ hard exam. Park it, move on, come back.

### Mindset

You've scored **87–92%** on every recent mock. Pass = **70%**. You have
**~17 percentage points of headroom**. Trust the prep.

<!-- markdownlint-disable-next-line MD036 -->
**Vas a romperla. 🎯🏆**

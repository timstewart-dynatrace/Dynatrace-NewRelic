# New Relic to Dynatrace Migration Tool

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A universal, comprehensive migration framework for converting New Relic monitoring configurations to Dynatrace.

## Overview

This tool automates the migration of monitoring configurations from New Relic to Dynatrace, handling the export, transformation, and import of all major monitoring components.

```mermaid
flowchart LR
    subgraph NR[" New Relic "]
        D1[("Dashboards")]
        A1[("Alerts")]
        S1[("Synthetics")]
        SLO1[("SLOs")]
        W1[("Workloads")]
    end

    subgraph Tool[" Migration Tool "]
        E["Export"]
        T["Transform"]
        I["Import"]
        E --> T --> I
    end

    subgraph DT[" Dynatrace "]
        D2[("Dashboards")]
        A2[("Metric Events")]
        S2[("HTTP/Browser\nMonitors")]
        SLO2[("SLOs")]
        W2[("Management\nZones")]
    end

    NR --> E
    I --> DT

    style NR fill:#1CE783,stroke:#333,color:#000
    style Tool fill:#4A90D9,stroke:#333,color:#fff
    style DT fill:#6F2DA8,stroke:#333,color:#fff
```

## Supported Components

| Component | New Relic | → | Dynatrace | Status |
|-----------|-----------|---|-----------|--------|
| **Dashboards** | Dashboard (multi-page) | → | Dashboard | ✅ Full |
| **Alerts** | Alert Policy + NRQL Conditions | → | Alerting Profile + Metric Events | ✅ Full |
| **Synthetics** | Ping/Browser/API Monitors | → | HTTP/Browser Monitors | ✅ Full |
| **SLOs** | Service Level Objectives | → | SLOs | ✅ Full |
| **Workloads** | Entity Groupings | → | Management Zones | ✅ Full |
| **Notifications** | Channels (Email, Slack, etc.) | → | Problem Notifications | ✅ Full |

## Architecture

```mermaid
flowchart TB
    subgraph Export["Phase 1: Export"]
        NR_API["New Relic\nNerdGraph API"]
        NR_Client["NewRelicClient"]
        Export_JSON[("Export\nJSON")]

        NR_API --> NR_Client --> Export_JSON
    end

    subgraph Transform["Phase 2: Transform"]
        DT["DashboardTransformer"]
        AT["AlertTransformer"]
        ST["SyntheticTransformer"]
        SLOT["SLOTransformer"]
        WT["WorkloadTransformer"]

        Mapping["Mapping Rules"]
        Transform_JSON[("Dynatrace\nJSON")]

        DT & AT & ST & SLOT & WT --> Mapping --> Transform_JSON
    end

    subgraph Import["Phase 3: Import"]
        DT_Client["DynatraceClient"]
        DT_API["Dynatrace\nSettings API v2"]
        Report[("Migration\nReport")]

        DT_Client --> DT_API --> Report
    end

    Export_JSON --> Transform
    Transform_JSON --> Import

    style Export fill:#1CE783,stroke:#333
    style Transform fill:#4A90D9,stroke:#333
    style Import fill:#6F2DA8,stroke:#333
```

## NRQL to DQL Converter

A standalone utility for converting New Relic Query Language (NRQL) to Dynatrace Query Language (DQL).

```bash
# Convert a single query
python nrql_to_dql.py "SELECT average(duration) FROM Transaction WHERE appName = 'MyApp'"

# Interactive mode
python nrql_to_dql.py --interactive

# Show reference table
python nrql_to_dql.py --reference
```

### Quick Reference

| NRQL | DQL |
|------|-----|
| `SELECT * FROM Log` | `fetch logs` |
| `SELECT count(*) FROM Transaction` | `fetch ... \| summarize count()` |
| `WHERE field = 'value'` | `\| filter field == "value"` |
| `WHERE field LIKE '%pattern%'` | `\| filter matchesPhrase(field, "pattern")` |
| `FACET fieldName` | `\| summarize by: {fieldName}` |
| `SINCE 1 hour ago` | `from:now()-1h` |
| `LIMIT 100` | `\| limit 100` |
| `average(field)` | `avg(field)` |
| `uniqueCount(field)` | `countDistinct(field)` |

### Example Conversion

```mermaid
flowchart LR
    subgraph NRQL["NRQL Query"]
        NQ["SELECT average(duration)<br/>FROM Transaction<br/>WHERE appName = 'MyApp'<br/>FACET host<br/>SINCE 1 hour ago"]
    end

    subgraph DQL["DQL Query"]
        DQ["fetch dt.entity.service, from:now()-1h<br/>| filter service.name == 'MyApp'<br/>| summarize avg(response_time),<br/>  by: {host.name}"]
    end

    NRQL -->|"nrql_to_dql.py"| DQL

    style NRQL fill:#1CE783,stroke:#333
    style DQL fill:#6F2DA8,stroke:#333
```

---

## Quick Start

### 1. Installation

```bash
git clone https://github.com/timstewart-dynatrace/Dynatrace-NewRelic.git
cd Dynatrace-NewRelic/newrelic-to-dynatrace-migration
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file or set environment variables:

```bash
# New Relic
NEW_RELIC_API_KEY=NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXX
NEW_RELIC_ACCOUNT_ID=1234567
NEW_RELIC_REGION=US  # or EU

# Dynatrace
DYNATRACE_API_TOKEN=dt0c01.XXXXXXXXXXXXXXXXXXXXXXXX
DYNATRACE_ENVIRONMENT_URL=https://abc12345.live.dynatrace.com
```

### 3. Run Migration

```bash
# Dry run first (validates without making changes)
python migrate.py --dry-run --full

# Full migration
python migrate.py --full

# Specific components only
python migrate.py --components dashboards,alerts
```

## CLI Reference

```mermaid
flowchart LR
    CLI["migrate.py"]

    CLI --> Full["--full\nComplete migration"]
    CLI --> Export["--export-only\nExport from NR"]
    CLI --> Import["--import-only\nImport to DT"]
    CLI --> Components["--components\nSelect specific"]
    CLI --> DryRun["--dry-run\nValidate only"]
    CLI --> List["--list-components\nShow available"]

    style CLI fill:#4A90D9,stroke:#333,color:#fff
```

| Command | Description |
|---------|-------------|
| `python migrate.py --full` | Complete migration (export → transform → import) |
| `python migrate.py --export-only` | Export from New Relic only |
| `python migrate.py --import-only --input ./path` | Import to Dynatrace from previous export |
| `python migrate.py --components dashboards,alerts` | Migrate specific components |
| `python migrate.py --dry-run` | Validate without making changes |
| `python migrate.py --list-components` | List available components |

## Entity Mapping

```mermaid
flowchart LR
    subgraph NR["New Relic"]
        NRD["Dashboard\n(multi-page)"]
        NRA["Alert Policy\n+ Conditions"]
        NRS["Synthetic\nMonitor"]
        NRSLO["SLO"]
        NRW["Workload"]
        NRN["Notification\nChannel"]
    end

    subgraph DT["Dynatrace"]
        DTD["Dashboard\n(per page)"]
        DTA["Alerting Profile\n+ Metric Events"]
        DTS["HTTP/Browser\nMonitor"]
        DTSLO["SLO"]
        DTW["Management\nZone"]
        DTN["Problem\nNotification"]
    end

    NRD -->|"1:N"| DTD
    NRA -->|"1:1 + 1:N"| DTA
    NRS -->|"1:1"| DTS
    NRSLO -->|"1:1"| DTSLO
    NRW -->|"1:1"| DTW
    NRN -->|"1:1"| DTN

    style NR fill:#1CE783,stroke:#333
    style DT fill:#6F2DA8,stroke:#333
```

### Detailed Mapping Table

| New Relic | Dynatrace | Notes |
|-----------|-----------|-------|
| Dashboard | Dashboard | Each page becomes a separate dashboard |
| Alert Policy | Alerting Profile | 1:1 mapping |
| NRQL Condition | Metric Event | Query conversion (limited automation) |
| APM Condition | Auto-Adaptive Baseline | Manual review recommended |
| Synthetic (Ping) | HTTP Monitor | Direct mapping |
| Synthetic (Browser) | Browser Monitor | Script adaptation needed |
| Synthetic (API) | HTTP Monitor (Multi-step) | Script adaptation needed |
| SLO | SLO | Metric expression mapping |
| Workload | Management Zone | Entity selector rules |
| Email Channel | Email Notification | Direct mapping |
| Slack Channel | Slack Notification | Webhook URL update needed |
| PagerDuty | PagerDuty Integration | Service key recreation |
| Webhook | Webhook Notification | Payload format adjustment |

## Project Structure

```
Dynatrace-NewRelic/
├── README.md                              # This file
├── CLAUDE.md                              # Development documentation
├── CLAUDE-for-NR.md                       # Research & reference guide
├── .gitignore
│
└── newrelic-to-dynatrace-migration/
    ├── migrate.py                         # Migration CLI entry point
    ├── nrql_to_dql.py                     # NRQL → DQL converter utility
    ├── requirements.txt                   # Python dependencies
    ├── .env.example                       # Environment template
    │
    ├── config/
    │   ├── __init__.py
    │   └── settings.py                    # Configuration (pydantic)
    │
    ├── clients/
    │   ├── __init__.py
    │   ├── newrelic_client.py             # NerdGraph GraphQL client
    │   └── dynatrace_client.py            # Settings API v2 client
    │
    ├── transformers/
    │   ├── __init__.py
    │   ├── mapping_rules.py               # Entity mappings
    │   ├── dashboard_transformer.py
    │   ├── alert_transformer.py
    │   ├── synthetic_transformer.py
    │   ├── slo_transformer.py
    │   └── workload_transformer.py
    │
    └── utils/
        ├── __init__.py
        ├── logger.py                      # Structured logging
        └── validators.py                  # Config validation
```

## Required API Permissions

### New Relic API Key

| Permission | Required For |
|------------|--------------|
| NerdGraph access | All exports |
| Dashboards (read) | Dashboard export |
| Alerts (read) | Alert policy/condition export |
| Synthetics (read) | Monitor export |
| Service Levels (read) | SLO export |
| Workloads (read) | Workload export |

### Dynatrace API Token

| Scope | Required For |
|-------|--------------|
| `settings.read` | Reading existing configs |
| `settings.write` | Creating alerting profiles, management zones |
| `WriteConfig` | Creating dashboards |
| `ReadConfig` | Reading existing configs |
| `ExternalSyntheticIntegration` | Creating synthetic monitors |
| `slo.read` / `slo.write` | SLO operations |

## Migration Workflow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant NR as New Relic API
    participant Transform as Transformers
    participant DT as Dynatrace API

    User->>CLI: migrate.py --full

    rect rgb(28, 231, 131)
        Note over CLI,NR: Phase 1: Export
        CLI->>NR: Fetch dashboards
        CLI->>NR: Fetch alert policies
        CLI->>NR: Fetch synthetics
        CLI->>NR: Fetch SLOs
        CLI->>NR: Fetch workloads
        NR-->>CLI: JSON exports
    end

    rect rgb(74, 144, 217)
        Note over CLI,Transform: Phase 2: Transform
        CLI->>Transform: Dashboard data
        CLI->>Transform: Alert data
        CLI->>Transform: Synthetic data
        Transform-->>CLI: Dynatrace format + warnings
    end

    rect rgb(111, 45, 168)
        Note over CLI,DT: Phase 3: Import
        CLI->>DT: Create dashboards
        CLI->>DT: Create alerting profiles
        CLI->>DT: Create metric events
        CLI->>DT: Create monitors
        DT-->>CLI: Import results
    end

    CLI-->>User: Migration report
```

## Known Limitations

| Area | Limitation | Workaround |
|------|------------|------------|
| **NRQL → DQL** | Limited automatic conversion | Manual query review |
| **Scripted Synthetics** | Complex scripts not converted | Manual recreation |
| **Entity References** | GUIDs don't map to DT IDs | Manual linking |
| **Dashboard Variables** | Limited filter conversion | Manual configuration |
| **Dynamic Baselines** | Not automatically converted | Manual threshold setup |
| **Historical Data** | Not transferable | N/A |

## Output Files

After running migration:

```
output/
├── exports/
│   └── newrelic_export.json       # Raw New Relic data
├── transformed/
│   └── dynatrace_config.json      # Transformed configs
└── reports/
    └── migration_report_*.json    # Detailed results
```

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](./CLAUDE.md) | Development guide, architecture details |
| [CLAUDE-for-NR.md](./CLAUDE-for-NR.md) | Research, GitHub tools, NRQL→DQL reference |
| [Tool README](./newrelic-to-dynatrace-migration/README.md) | Detailed usage guide |

## Related Resources

- [New Relic NerdGraph API](https://docs.newrelic.com/docs/apis/nerdgraph/)
- [Dynatrace Settings API v2](https://docs.dynatrace.com/docs/dynatrace-api/environment-api/settings)
- [Dynatrace Monaco CLI](https://docs.dynatrace.com/docs/deliver/configuration-as-code/monaco)
- [Dynatrace Terraform Provider](https://github.com/dynatrace-oss/terraform-provider-dynatrace)

## Contributing

1. Update `CLAUDE.md` with any changes
2. Follow commit conventions (feat/fix/docs/refactor)
3. Push to GitHub after major changes

## License

MIT License - See LICENSE file for details.

---

**Note**: This tool was created to address the lack of existing New Relic → Dynatrace migration solutions. See [CLAUDE-for-NR.md](./CLAUDE-for-NR.md) for research findings.

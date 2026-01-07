# New Relic to Dynatrace Universal Migration Tool

A comprehensive, generic migration framework for converting New Relic monitoring configurations to Dynatrace.

## Overview

This tool provides a complete solution for migrating all monitoring configurations from New Relic to Dynatrace, including:

- **Dashboards** - Visualization and reporting
- **Alerts/Alert Policies** - Alerting configurations and conditions
- **Synthetic Monitors** - Availability and browser-based testing
- **APM Configurations** - Application performance monitoring settings
- **Infrastructure Monitoring** - Host and infrastructure configurations
- **Service Level Objectives (SLOs)** - Performance targets
- **Workloads** - Entity groupings
- **Notification Channels** - Alert delivery mechanisms

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    New Relic to Dynatrace Migration Tool                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │   EXPORTER   │    │  TRANSFORMER │    │        IMPORTER          │  │
│  │              │    │              │    │                          │  │
│  │ New Relic    │───▶│   Mapping    │───▶│  Dynatrace               │  │
│  │ NerdGraph    │    │   Engine     │    │  Settings API v2         │  │
│  │ API          │    │              │    │  Configuration API       │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│         │                   │                        │                  │
│         ▼                   ▼                        ▼                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │ Export JSON  │    │ Mapped JSON  │    │  Import Report           │  │
│  │ (backup)     │    │ (Dynatrace)  │    │  (success/failures)      │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.9+
- New Relic User API Key (with appropriate permissions)
- Dynatrace API Token (with appropriate scopes)

## Installation

```bash
cd newrelic-to-dynatrace-migration
pip install -r requirements.txt
```

## Configuration

Create a `.env` file or set environment variables:

```bash
# New Relic Configuration
NEW_RELIC_API_KEY=NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXX
NEW_RELIC_ACCOUNT_ID=1234567

# Dynatrace Configuration
DYNATRACE_API_TOKEN=dt0c01.XXXXXXXXXXXXXXXXXXXXXXXX
DYNATRACE_ENVIRONMENT_URL=https://abc12345.live.dynatrace.com
```

## Usage

### Full Migration
```bash
python migrate.py --full
```

### Export Only (from New Relic)
```bash
python migrate.py --export-only --output ./exports/
```

### Import Only (to Dynatrace)
```bash
python migrate.py --import-only --input ./exports/transformed/
```

### Selective Migration
```bash
# Migrate only dashboards
python migrate.py --components dashboards

# Migrate multiple components
python migrate.py --components dashboards,alerts,synthetics

# Dry run (validate without applying)
python migrate.py --dry-run --components alerts
```

### List Available Components
```bash
python migrate.py --list-components
```

## Entity Mapping Reference

| New Relic Concept | Dynatrace Equivalent |
|-------------------|---------------------|
| Dashboard | Dashboard |
| Alert Policy | Alerting Profile |
| Alert Condition (NRQL) | Metric Event / Custom Alert |
| Alert Condition (APM) | Auto-Adaptive Baseline Alert |
| Synthetic Monitor (Ping) | HTTP Monitor |
| Synthetic Monitor (Scripted Browser) | Browser Monitor |
| Synthetic Monitor (Scripted API) | HTTP Monitor (Multi-step) |
| Notification Channel | Alerting Integration |
| Workload | Management Zone |
| SLO | SLO (native) |
| APM Service | Service (auto-detected) |
| Infrastructure Host | Host (auto-detected) |

## Project Structure

```
newrelic-to-dynatrace-migration/
├── migrate.py                 # Main entry point
├── requirements.txt           # Python dependencies
├── config/
│   └── settings.py           # Configuration management
├── exporters/
│   ├── __init__.py
│   ├── base_exporter.py      # Base exporter class
│   ├── dashboard_exporter.py # Dashboard export logic
│   ├── alert_exporter.py     # Alert export logic
│   ├── synthetic_exporter.py # Synthetic monitor export
│   ├── apm_exporter.py       # APM configuration export
│   ├── slo_exporter.py       # SLO export logic
│   └── workload_exporter.py  # Workload export logic
├── transformers/
│   ├── __init__.py
│   ├── base_transformer.py   # Base transformer class
│   ├── dashboard_transformer.py
│   ├── alert_transformer.py
│   ├── synthetic_transformer.py
│   └── mapping_rules.py      # Mapping configuration
├── importers/
│   ├── __init__.py
│   ├── base_importer.py      # Base importer class
│   ├── dashboard_importer.py
│   ├── alert_importer.py
│   ├── synthetic_importer.py
│   └── settings_importer.py  # Settings 2.0 API importer
├── clients/
│   ├── __init__.py
│   ├── newrelic_client.py    # New Relic NerdGraph client
│   └── dynatrace_client.py   # Dynatrace API client
├── models/
│   ├── __init__.py
│   ├── newrelic_models.py    # New Relic data models
│   └── dynatrace_models.py   # Dynatrace data models
├── utils/
│   ├── __init__.py
│   ├── logger.py             # Logging utilities
│   └── validators.py         # Validation helpers
└── tests/
    └── ...                   # Test files
```

## License

MIT License

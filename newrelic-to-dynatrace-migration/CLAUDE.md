# CLAUDE.md - Project Documentation

> **IMPORTANT**: This file MUST be kept current with all project changes. Update this file with every major edit and commit to GitHub.

## Project Overview

**Repository**: Dynatrace-NewRelic
**Purpose**: Universal migration tool for converting New Relic monitoring configurations to Dynatrace
**Last Updated**: 2026-01-07
**Status**: Initial Development

## Quick Start

```bash
cd newrelic-to-dynatrace-migration
pip install -r requirements.txt

# Configure environment
export NEW_RELIC_API_KEY=NRAK-XXXXXXXXXXXX
export NEW_RELIC_ACCOUNT_ID=1234567
export DYNATRACE_API_TOKEN=dt0c01.XXXXXXXXXXXX
export DYNATRACE_ENVIRONMENT_URL=https://abc12345.live.dynatrace.com

# Run full migration
python migrate.py --full

# Or dry run first
python migrate.py --dry-run
```

## Project Structure

```
Dynatrace-NewRelic/
├── CLAUDE.md                          # THIS FILE - Keep updated!
├── newrelic-to-dynatrace-migration/
│   ├── migrate.py                     # Main CLI entry point
│   ├── requirements.txt               # Python dependencies
│   ├── README.md                      # User documentation
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py               # Configuration management (pydantic)
│   │
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── newrelic_client.py        # New Relic NerdGraph API client
│   │   └── dynatrace_client.py       # Dynatrace Settings/Config API client
│   │
│   ├── transformers/
│   │   ├── __init__.py
│   │   ├── mapping_rules.py          # Entity mapping definitions
│   │   ├── dashboard_transformer.py  # Dashboard conversion
│   │   ├── alert_transformer.py      # Alert/metric event conversion
│   │   ├── synthetic_transformer.py  # Synthetic monitor conversion
│   │   ├── slo_transformer.py        # SLO conversion
│   │   └── workload_transformer.py   # Workload → Management Zone
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                 # Structured logging (structlog)
│       └── validators.py             # Configuration validators
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Migration Pipeline                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  EXPORT              TRANSFORM              IMPORT                       │
│  ──────              ─────────              ──────                       │
│  New Relic    ───►   Mapping     ───►       Dynatrace                   │
│  NerdGraph           Engine                 Settings API v2              │
│  GraphQL API                                Configuration API            │
│                                                                          │
│  Entities:           Transformers:          Targets:                     │
│  • Dashboards        • DashboardTransformer • Dashboards                 │
│  • Alert Policies    • AlertTransformer     • Alerting Profiles          │
│  • Conditions        • SyntheticTransformer • Metric Events              │
│  • Synthetics        • SLOTransformer       • HTTP/Browser Monitors      │
│  • SLOs             • WorkloadTransformer   • SLOs                       │
│  • Workloads                                • Management Zones           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Entity Mapping Reference

| New Relic                    | Dynatrace                     | Notes                           |
|------------------------------|-------------------------------|--------------------------------|
| Dashboard                    | Dashboard                     | Multi-page → multiple dashboards |
| Dashboard Page               | Dashboard                     | Each page becomes separate      |
| Dashboard Widget             | Tile                          | Visualization mapping required  |
| Alert Policy                 | Alerting Profile              | 1:1 mapping                     |
| NRQL Alert Condition         | Metric Event (Custom Alert)   | Query conversion needed         |
| APM Alert Condition          | Auto-Adaptive Baseline        | Limited automatic conversion    |
| Synthetic Monitor (Ping)     | HTTP Monitor                  | Direct mapping                  |
| Synthetic Monitor (Browser)  | Browser Monitor               | Script conversion limited       |
| Synthetic Monitor (API)      | HTTP Monitor (Multi-step)     | Script conversion limited       |
| SLO                          | SLO                           | Metric expression mapping       |
| Workload                     | Management Zone               | Rule-based conversion           |
| Notification Channel         | Problem Notification          | Type-specific mapping           |

## Key Components

### 1. NewRelicClient (`clients/newrelic_client.py`)
- Uses NerdGraph GraphQL API
- Handles pagination automatically
- Rate limiting built-in
- Methods: `get_all_dashboards()`, `get_all_alert_policies()`, `get_all_synthetic_monitors()`, `get_all_slos()`, `get_all_workloads()`

### 2. DynatraceClient (`clients/dynatrace_client.py`)
- Uses Settings API v2 and Configuration API v1
- Supports both SaaS and Managed
- Methods: `create_dashboard()`, `create_metric_event()`, `create_alerting_profile()`, `create_http_monitor()`, `create_slo()`, `create_management_zone()`

### 3. Transformers
Each transformer:
- Takes New Relic export format
- Returns Dynatrace-compatible format
- Includes warnings for manual review items
- Handles edge cases gracefully

### 4. Mapping Rules (`transformers/mapping_rules.py`)
Central location for all value mappings:
- `VISUALIZATION_TYPE_MAP` - Widget types
- `ALERT_PRIORITY_MAP` - Severity levels
- `SYNTHETIC_MONITOR_TYPE_MAP` - Monitor types
- `MONITOR_PERIOD_MAP` - Frequency values

## CLI Usage

```bash
# Full migration
python migrate.py --full

# Export only (no Dynatrace import)
python migrate.py --export-only --output ./my-export

# Import only (from previous export)
python migrate.py --import-only --input ./my-export

# Specific components
python migrate.py --components dashboards,alerts

# Dry run (validate without changes)
python migrate.py --dry-run

# List available components
python migrate.py --list-components
```

## Environment Variables

| Variable                    | Required | Description                              |
|-----------------------------|----------|------------------------------------------|
| `NEW_RELIC_API_KEY`         | Yes      | User API key (starts with NRAK-)         |
| `NEW_RELIC_ACCOUNT_ID`      | Yes      | Numeric account ID                       |
| `NEW_RELIC_REGION`          | No       | US (default) or EU                       |
| `DYNATRACE_API_TOKEN`       | Yes      | API token (starts with dt0c01.)          |
| `DYNATRACE_ENVIRONMENT_URL` | Yes      | https://<id>.live.dynatrace.com          |
| `MIGRATION_DRY_RUN`         | No       | Set to "true" for dry run mode           |
| `LOG_LEVEL`                 | No       | INFO (default), DEBUG, WARNING, ERROR    |

## Required API Permissions

### New Relic API Key Scopes
- `NerdGraph` - Full access
- Specifically needs access to:
  - Dashboards (read)
  - Alerts (read)
  - Synthetics (read)
  - Service Levels (read)
  - Workloads (read)
  - Notification Channels (read)

### Dynatrace API Token Scopes
- `settings.read` - Read settings
- `settings.write` - Write settings
- `WriteConfig` - Configuration API write
- `ReadConfig` - Configuration API read
- `ExternalSyntheticIntegration` - Synthetic monitors
- `slo.read` - Read SLOs
- `slo.write` - Write SLOs

## Known Limitations

1. **NRQL to DQL Conversion**: Limited automatic conversion. Complex queries require manual adjustment.

2. **Scripted Synthetics**: Browser and API scripts cannot be fully converted. Basic navigation is created; complex logic needs manual recreation.

3. **Entity References**: New Relic GUIDs don't map to Dynatrace entity IDs. References may need manual linking.

4. **Dashboard Variables**: Limited conversion to Dynatrace dashboard filters.

5. **Alert Thresholds**: Static thresholds convert well; dynamic baselines require manual configuration.

## Development Guidelines

### Adding a New Transformer
1. Create `transformers/new_transformer.py`
2. Implement `transform()` and `transform_all()` methods
3. Return `TransformResult` dataclass with success/warnings/errors
4. Add mapping rules to `mapping_rules.py`
5. Register in `transformers/__init__.py`
6. Add to `MigrationOrchestrator` in `migrate.py`

### Testing
```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=. tests/
```

### Code Style
- Python 3.9+
- Type hints required
- Docstrings for public methods
- Use structlog for logging

## Changelog

### 2026-01-07 - Initial Version
- Created complete migration framework
- Implemented New Relic NerdGraph client
- Implemented Dynatrace API clients
- Added transformers for:
  - Dashboards
  - Alerts (policies, conditions, notifications)
  - Synthetic monitors (HTTP, Browser)
  - SLOs
  - Workloads → Management Zones
- CLI with rich progress display
- Export/transform/import phases
- Dry run support
- Migration reports

## Maintenance Checklist

When making changes:

- [ ] Update this CLAUDE.md file
- [ ] Update README.md if user-facing changes
- [ ] Add/update tests
- [ ] Update mapping rules if new entity types
- [ ] Commit with descriptive message
- [ ] Push to GitHub

## Commit Convention

```
<type>: <description>

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- refactor: Code refactoring
- test: Tests
- chore: Maintenance
```

## Support Resources

- [CLAUDE-for-NR.md](./CLAUDE-for-NR.md) - Research document with GitHub tools and community solutions
- [New Relic NerdGraph API](https://docs.newrelic.com/docs/apis/nerdgraph/)
- [Dynatrace Settings API v2](https://docs.dynatrace.com/docs/dynatrace-api/environment-api/settings)
- [Dynatrace Configuration API](https://docs.dynatrace.com/docs/dynatrace-api/configuration-api)
- [Dynatrace Monaco CLI](https://docs.dynatrace.com/docs/deliver/configuration-as-code/monaco)
- [Dynatrace Terraform Provider](https://github.com/dynatrace-oss/terraform-provider-dynatrace)
- [New Relic Account Migration Tool](https://github.com/newrelic-experimental/nr-account-migration)

## Related Documentation

See [CLAUDE-for-NR.md](./CLAUDE-for-NR.md) for:
- Available GitHub repositories and tools for both platforms
- OpenTelemetry migration path as intermediate layer
- NRQL to DQL conversion reference table
- Community discussions and resources
- Recommended step-by-step migration workflow
- Known limitations and feature gaps

---

**Remember**: Keep this file updated with every significant change!

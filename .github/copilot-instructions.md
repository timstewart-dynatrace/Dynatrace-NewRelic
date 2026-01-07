# Copilot Instructions - Dynatrace-NewRelic

## Project Overview

**Dynatrace-NewRelic** is a migration toolkit with two complementary tools:

1. **NRQL to DQL Converter** - Lightweight standalone query converter
2. **Migration Framework** - Full configuration migration pipeline

## Architecture & Key Patterns

### Migration Pipeline (newrelic-to-dynatrace-migration/)

```
Export (New Relic GraphQL) → Transform (Mapper classes) → Import (Dynatrace API)
```

**Key Components:**

- `config/settings.py` - Pydantic BaseSettings for API credentials and URLs. Handles region-specific endpoints (US vs EU)
- `clients/` - GraphQL (New Relic) and REST/Settings API (Dynatrace) clients with error handling
- `transformers/` - Entity-specific converters (dashboard, alert, synthetic, SLO, workload)
- `migrate.py` - Click CLI entry point orchestrating the full pipeline

**Critical Pattern:** Each transformer inherits from base transformation logic, returns `TransformResult` dataclass with `success`, `data`, `warnings`, `errors`.

### NRQL to DQL Converter (nrql-converter/)

Standalone tool converting NRQL queries to DQL. Uses regex-based pattern matching to:

- Parse SELECT, WHERE, FACET, SINCE, LIMIT clauses
- Map aggregation functions (uniqueCount → countDistinct, average → avg)
- Convert time ranges (-30m, -1h, -7d format)
- Apply field mapping (appName → service.name, duration → response_time)
- Return `ConversionResult` with confidence scoring and field mappings applied

**Run tests:** `python -m pytest test_nrql_to_dql.py -v` (21 tests, all passing)

## Entity Mapping Reference

| New Relic              | Dynatrace            | Notes                                |
| ---------------------- | -------------------- | ------------------------------------ |
| Dashboard (multi-page) | Multiple Dashboards  | Each page becomes separate dashboard |
| Alert Policy           | Alerting Profile     | 1:1 mapping                          |
| NRQL Condition         | Metric Event         | Needs query conversion               |
| Synthetic Monitor      | HTTP/Browser Monitor | Direct mapping for Ping → HTTP       |
| SLO                    | SLO                  | Query conversion required            |
| Workload               | Management Zone      | Conceptual mapping                   |

See `newrelic-to-dynatrace-migration/transformers/mapping_rules.py` for complete FieldMapping definitions.

## Development Workflow

### Setup

```bash
cd newrelic-to-dynatrace-migration
pip install -r requirements.txt
# Set env vars: NEW_RELIC_API_KEY, DYNATRACE_API_TOKEN, etc.
```

### Testing

- **Migration tests:** `pytest tests/` (if added)
- **Converter tests:** `cd nrql-converter && pytest test_nrql_to_dql.py -v`
- **Dry-run verification:** `python migrate.py --dry-run --full`

### Configuration

- Environment variables via `.env` (use `.env.example` as template)
- Pydantic validates required fields at startup; `settings.py` handles region-specific URLs

## Code Conventions

1. **Logging:** Use `structlog` (not `logging`). Initialized in `migrate.py` with ISO timestamps and dev renderer
2. **Error Handling:** Transformers return `TransformResult` dataclass; CLI bubbles up errors as exit codes
3. **API Clients:** Separate New Relic (GraphQL) and Dynatrace (REST) clients; handle pagination in client, not caller
4. **Field Mapping:** Define in `mapping_rules.py` using `FieldMapping` dataclass with `TransformationType` enum (DIRECT, MAPPED, COMPUTED, TEMPLATE, CUSTOM)
5. **CLI Design:** Use Click decorators; progress shown via `rich.Progress`; dry-run doesn't apply changes

## Common Tasks

**Add new component migration:**

1. Create transformer class in `transformers/new_transformer.py` inheriting transformation patterns
2. Define entity mappings in `mapping_rules.py`
3. Register in `migrate.py` CLI under `--components` option
4. Add test coverage

**Fix NRQL conversion:**

- Update regex patterns in `nrql_to_dql.py`
- Add test case to `test_nrql_to_dql.py`
- Update mappings in `examples.nrql` if pattern changes apply broadly

**Handle API changes:**

- For New Relic: Update GraphQL queries in `clients/newrelic_client.py`
- For Dynatrace: Check Settings/Config API v2 docs; update request schema in `clients/dynatrace_client.py`

## Key Files & Decision Points

| File                 | When to Update         | What It Controls                      |
| -------------------- | ---------------------- | ------------------------------------- |
| `mapping_rules.py`   | Adding fields/entities | Entity transformation logic           |
| `migrate.py`         | Adding CLI options     | Migration workflow & orchestration    |
| `config/settings.py` | New config needed      | Credential/environment handling       |
| `nrql_to_dql.py`     | Query pattern fixes    | NRQL → DQL conversion                 |
| `CLAUDE.md`          | Major changes          | Project documentation (keep current!) |

## External Dependencies

- **New Relic:** GraphQL endpoint (region-specific), API v1/v2 REST APIs
- **Dynatrace:** Settings API v2, Config API, API token required
- **Python libs:** Click (CLI), Pydantic (config), structlog (logging), Rich (output), GraphQL-core (New Relic client), requests (HTTP)

## Debugging Tips

1. **API Failures:** Check `.env` credentials and region settings; dry-run mode logs API requests
2. **Transformation Issues:** Enable structlog debug level to see field mapping details
3. **Test Failures:** Converter tests fail if `ConversionResult.converted_dql` doesn't match expected pattern — check regex changes
4. **Pagination:** Clients handle pagination internally; if incomplete data returned, check GraphQL query limits

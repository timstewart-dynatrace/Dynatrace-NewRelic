# NRQL to DQL Converter

A comprehensive Python tool for converting New Relic Query Language (NRQL) queries to Dynatrace Query Language (DQL).

## Overview

This tool helps users migrate from New Relic to Dynatrace by automatically converting NRQL queries to their DQL equivalents. It handles common query patterns including aggregations, filtering, grouping, time ranges, and provides confidence scoring for each conversion.

## Features

- **Interactive Mode**: Real-time query conversion with rich CLI interface
- **Batch Processing**: Convert multiple queries from a file
- **Reference Tables**: Built-in quick reference for common conversions
- **Confidence Scoring**: High/Medium/Low confidence ratings for conversions
- **Field Mapping**: Automatic mapping of New Relic fields to Dynatrace equivalents
- **Warning System**: Alerts for queries that may need manual review
- **Rich Output**: Syntax-highlighted DQL output with conversion details

### Supported Conversions

- SELECT clause with aggregations (count, avg, sum, min, max, percentile, etc.)
- FROM clause with event type mapping
- WHERE clause with operators (=, !=, <, >, LIKE, IN, IS NULL)
- FACET (group by) clauses
- Time range expressions (SINCE, UNTIL)
- LIMIT clauses
- TIMESERIES queries

## Installation

```bash
cd nrql-converter
pip install -r requirements.txt
chmod +x nrql_to_dql.py
```

## Usage

### Command Line

Convert a single query:

```bash
./nrql_to_dql.py "SELECT count(*) FROM Transaction WHERE appName = 'MyApp' SINCE 1 hour ago"
```

### Interactive Mode

```bash
./nrql_to_dql.py --interactive
```

In interactive mode:
- Type NRQL queries to convert them
- Type `ref` or `reference` to see the quick reference table
- Type `quit` or `exit` to exit

### Show Reference Table

```bash
./nrql_to_dql.py --reference
```

### Batch Processing

Convert queries from a file:

```bash
./nrql_to_dql.py --file queries.nrql --output converted.dql
```

### As a Python Module

```python
from nrql_to_dql import NRQLtoDQLConverter

converter = NRQLtoDQLConverter()
result = converter.convert("SELECT count(*) FROM Transaction SINCE 1 hour ago")

print(f"DQL: {result.converted_dql}")
print(f"Confidence: {result.confidence}")
print(f"Warnings: {result.warnings}")
```

## Quick Reference

| NRQL | DQL |
|------|-----|
| `SELECT * FROM Log` | `fetch logs` |
| `SELECT count(*) FROM Transaction` | `fetch ... \| summarize count()` |
| `WHERE field = 'value'` | `\| filter field == "value"` |
| `WHERE field LIKE '%pattern%'` | `\| filter matchesPhrase(field, "pattern")` |
| `WHERE field IN ('a', 'b')` | `\| filter in(field, "a", "b")` |
| `WHERE field IS NULL` | `\| filter isNull(field)` |
| `FACET fieldName` | `\| summarize by: {fieldName}` |
| `SINCE 1 hour ago` | `from:now()-1h` |
| `LIMIT 100` | `\| limit 100` |

### Aggregation Functions

| NRQL | DQL |
|------|-----|
| `count(*)` | `count()` |
| `average(field)` | `avg(field)` |
| `sum(field)` | `sum(field)` |
| `max(field)` | `max(field)` |
| `min(field)` | `min(field)` |
| `uniqueCount(field)` | `countDistinct(field)` |
| `percentile(field, 95)` | `percentile(field, 95)` |
| `latest(field)` | `last(field)` |
| `earliest(field)` | `first(field)` |

### Field Mappings

| New Relic Field | Dynatrace Field |
|-----------------|-----------------|
| `duration` | `response_time` |
| `appName` | `service.name` |
| `host` | `host.name` |
| `httpResponseCode` | `http.status_code` |
| `cpuPercent` | `cpu.usage` |
| `message` | `content` |
| `level` | `loglevel` |

### Event Type Mappings

| New Relic Event | Dynatrace Data Type |
|-----------------|---------------------|
| `Transaction` | `timeseries` (service metrics) |
| `Log` | `logs` |
| `Span` | `spans` |
| `SystemSample` | `timeseries` (host metrics) |
| `PageView` | `bizevents` |
| `SyntheticCheck` | `timeseries` (synthetic metrics) |

## Examples

### Simple Aggregation

**NRQL:**
```sql
SELECT count(*) FROM Transaction SINCE 1 hour ago
```

**DQL:**
```sql
fetch dt.entity.service, from:now()-1h
| summarize count()
```

### Filtering with Aggregation

**NRQL:**
```sql
SELECT average(duration) FROM Transaction WHERE appName = 'MyApp' SINCE 24 hours ago
```

**DQL:**
```sql
fetch dt.entity.service, from:now()-24h
| filter service.name == 'MyApp'
| summarize avg(response_time)
```

### Grouping with FACET

**NRQL:**
```sql
SELECT count(*), average(duration) FROM Transaction FACET host SINCE 1 hour ago LIMIT 10
```

**DQL:**
```sql
fetch dt.entity.service, from:now()-1h
| summarize count(), avg(response_time), by: {host.name}
| limit 10
```

### Log Query

**NRQL:**
```sql
SELECT * FROM Log WHERE level = 'ERROR' SINCE 30 minutes ago
```

**DQL:**
```sql
fetch logs, from:now()-30m
| filter loglevel == 'ERROR'
```

## Output Format

The converter provides detailed output including:

1. **Converted DQL**: The transformed query
2. **Confidence Level**: High, Medium, or Low
3. **Field Mappings Applied**: Which fields were automatically mapped
4. **Warnings**: Issues that may affect query accuracy
5. **Manual Review Items**: Parts requiring human verification

## Limitations

- Complex nested queries may require manual adjustment
- Custom New Relic event types are mapped to `bizevents` by default
- Some New Relic-specific functions (funnel, histogram) don't have direct DQL equivalents
- COMPARE WITH clauses require manual implementation
- Advanced time expressions may need manual review

## Testing

Run the test suite:

```bash
python test_nrql_to_dql.py -v
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details.

# NRQL to DQL Converter

A Python tool to convert NewRelic NRQL (New Relic Query Language) queries to Dynatrace DQL (Dynatrace Query Language) queries.

## Overview

This tool helps users migrate from NewRelic to Dynatrace by automatically converting NRQL queries to their DQL equivalents. It handles common query patterns including aggregations, filtering, grouping, and time ranges.

## Features

- **SELECT clause conversion**: Converts field selections and aggregation functions
- **FROM clause mapping**: Maps NewRelic event types to Dynatrace record types
- **WHERE clause translation**: Converts filter conditions with proper DQL syntax
- **Time range conversion**: Transforms SINCE/UNTIL clauses to DQL timeframe filters
- **Aggregation functions**: Supports COUNT, AVG, SUM, MIN, MAX, uniqueCount, and more
- **FACET to GROUP BY**: Converts FACET clauses to DQL summarize with by clause
- **LIMIT support**: Preserves query result limits
- **Operator conversion**: Handles LIKE, AND, OR, comparison operators

## Installation

No external dependencies required - uses only Python 3 standard library.

```bash
chmod +x nrql_to_dql.py
```

## Usage

### Command Line

Convert a query directly from command line:

```bash
./nrql_to_dql.py "SELECT count(*) FROM Transaction WHERE appName = 'MyApp' SINCE 1 hour ago"
```

With verbose output:

```bash
./nrql_to_dql.py "SELECT count(*) FROM Transaction SINCE 1 hour ago" -v
```

From a file:

```bash
./nrql_to_dql.py -f input.nrql -o output.dql
```

### As a Python Module

```python
from nrql_to_dql import NRQLtoDQLConverter

converter = NRQLtoDQLConverter()
dql = converter.convert("SELECT count(*) FROM Transaction SINCE 1 hour ago")
print(dql)
```

## Examples

### Simple Count Query

**NRQL:**
```sql
SELECT count(*) FROM Transaction SINCE 1 hour ago
```

**DQL:**
```sql
fetch dt.entity.process_group_instance | filterTime -1h | summarize count()
```

### Aggregation with Filtering

**NRQL:**
```sql
SELECT average(duration) FROM Transaction WHERE appName = 'MyApp' SINCE 24 hours ago
```

**DQL:**
```sql
fetch dt.entity.process_group_instance | filter appName == 'MyApp' | filterTime -24h | summarize avg(duration)
```

### Group By (FACET) Query

**NRQL:**
```sql
SELECT count(*), average(duration) FROM Transaction FACET name SINCE 1 hour ago LIMIT 10
```

**DQL:**
```sql
fetch dt.entity.process_group_instance | filterTime -1h | summarize count(), avg(duration) by name | limit 10
```

### Complex Query with Multiple Conditions

**NRQL:**
```sql
SELECT count(*) FROM Transaction WHERE appName = 'MyApp' AND duration > 1000 FACET host SINCE 24 hours ago LIMIT 20
```

**DQL:**
```sql
fetch dt.entity.process_group_instance | filter appName == 'MyApp' and duration > 1000 | filterTime -24h | summarize count() by host | limit 20
```

### LIKE Operator Conversion

**NRQL:**
```sql
SELECT count(*) FROM Transaction WHERE name LIKE '%login%' SINCE 1 hour ago
```

**DQL:**
```sql
fetch dt.entity.process_group_instance | filter contains(name, 'login') | filterTime -1h | summarize count()
```

## Supported Conversions

### Functions

| NRQL Function | DQL Function |
|---------------|--------------|
| count() | count() |
| sum() | sum() |
| average() / avg() | avg() |
| min() | min() |
| max() | max() |
| uniqueCount() | countDistinct() |
| percentage() | percentage() |
| rate() | rate() |
| stddev() | stddev() |
| median() | median() |
| percentile() | percentile() |

### Event Types

| NRQL Event Type | DQL Record Type |
|-----------------|-----------------|
| Transaction | dt.entity.process_group_instance |
| TransactionError | dt.entity.process_group_instance |
| Metric | dt.metrics |
| Log | dt.entity.log |
| SystemSample | dt.entity.host |
| ProcessSample | dt.entity.process |

### Operators

| NRQL Operator | DQL Operator |
|---------------|--------------|
| = | == |
| LIKE '%text%' | contains(field, 'text') |
| LIKE 'text%' | startsWith(field, 'text') |
| LIKE '%text' | endsWith(field, 'text') |
| AND | and |
| OR | or |
| NOT | not |

### Time Ranges

| NRQL Time | DQL Time |
|-----------|----------|
| SINCE 30 minutes ago | -30m |
| SINCE 1 hour ago | -1h |
| SINCE 24 hours ago | -24h |
| SINCE 7 days ago | -7d |
| SINCE 1 week ago | -1w |

## Testing

Run the test suite:

```bash
python3 test_nrql_to_dql.py
```

Run with verbose output:

```bash
python3 test_nrql_to_dql.py -v
```

## Limitations

- Complex nested queries may require manual adjustment
- Custom NewRelic event types will be mapped using a generic pattern
- Some NewRelic-specific functions may not have direct DQL equivalents
- Advanced time expressions may need manual review

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source and available under the MIT License.

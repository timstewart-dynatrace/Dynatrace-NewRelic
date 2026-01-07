# Dynatrace-NewRelic

Utilities for migrating from NewRelic to Dynatrace.

## Tools

### NRQL to DQL Converter

A Python tool to convert NewRelic NRQL (New Relic Query Language) queries to Dynatrace DQL (Dynatrace Query Language) queries.

**Location:** `nrql-converter/`

This tool helps users migrate from NewRelic to Dynatrace by automatically converting NRQL queries to their DQL equivalents. It handles common query patterns including aggregations, filtering, grouping, and time ranges.

For detailed documentation, see [nrql-converter/README.md](nrql-converter/README.md)

#### Quick Start

```bash
cd nrql-converter
./nrql_to_dql.py "SELECT count(*) FROM Transaction WHERE appName = 'MyApp' SINCE 1 hour ago"
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source and available under the MIT License.


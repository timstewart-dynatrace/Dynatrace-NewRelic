#!/usr/bin/env python3
"""
NRQL to DQL Converter

A utility for converting New Relic Query Language (NRQL) queries
to Dynatrace Query Language (DQL).

Usage:
    python nrql_to_dql.py "SELECT average(duration) FROM Transaction WHERE appName = 'MyApp'"
    python nrql_to_dql.py --interactive
    python nrql_to_dql.py --file queries.txt
"""

import re
import sys
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


class QueryType(Enum):
    """Types of queries that can be converted."""
    METRICS = "metrics"
    LOGS = "logs"
    TRACES = "traces"
    EVENTS = "events"
    UNKNOWN = "unknown"


@dataclass
class ConversionResult:
    """Result of NRQL to DQL conversion."""
    original_nrql: str
    converted_dql: str
    query_type: QueryType
    confidence: str  # "high", "medium", "low"
    warnings: List[str] = field(default_factory=list)
    manual_review_needed: List[str] = field(default_factory=list)
    field_mappings_used: Dict[str, str] = field(default_factory=dict)


class NRQLtoDQLConverter:
    """
    Converts NRQL (New Relic Query Language) to DQL (Dynatrace Query Language).

    Key differences:
    - NRQL: SQL-like syntax (SELECT, FROM, WHERE, FACET)
    - DQL: Pipe-based syntax (fetch, filter, summarize, fieldsAdd)
    """

    # =========================================================================
    # Field Mappings: New Relic → Dynatrace
    # =========================================================================

    FIELD_MAPPINGS = {
        # Transaction/Service fields
        "duration": "response_time",
        "totalTime": "response_time",
        "webDuration": "response_time",
        "databaseDuration": "db.response_time",
        "externalDuration": "external.response_time",
        "name": "service.name",
        "transactionName": "span.name",
        "appName": "service.name",
        "appId": "dt.entity.service",
        "host": "host.name",
        "hostname": "host.name",

        # Error fields
        "error": "error",
        "error.class": "error.type",
        "error.message": "error.message",
        "errorMessage": "error.message",
        "errorType": "error.type",

        # HTTP fields
        "httpResponseCode": "http.status_code",
        "response.status": "http.status_code",
        "request.uri": "http.route",
        "request.method": "http.request.method",
        "http.url": "http.url",
        "http.method": "http.request.method",
        "http.statusCode": "http.status_code",

        # Infrastructure fields
        "cpuPercent": "cpu.usage",
        "memoryUsedPercent": "memory.usage",
        "diskUsedPercent": "disk.usage",
        "cpuSystemPercent": "cpu.system",
        "cpuUserPercent": "cpu.user",
        "memoryFreeBytes": "memory.free",
        "memoryTotalBytes": "memory.total",

        # Log fields
        "message": "content",
        "log.message": "content",
        "level": "loglevel",
        "log.level": "loglevel",
        "severity": "loglevel",

        # Common fields
        "timestamp": "timestamp",
        "entityGuid": "dt.entity.service",
        "entity.guid": "dt.entity.service",
        "tags": "tags",
    }

    # =========================================================================
    # Event Type Mappings: New Relic Event → Dynatrace Data Type
    # =========================================================================

    EVENT_TYPE_MAPPINGS = {
        # APM Events
        "Transaction": ("timeseries", "builtin:service.response.time"),
        "TransactionError": ("timeseries", "builtin:service.errors.total.count"),
        "Span": ("spans", None),
        "DistributedTrace": ("spans", None),

        # Infrastructure Events
        "SystemSample": ("timeseries", "builtin:host.cpu.usage"),
        "ProcessSample": ("timeseries", "builtin:tech.process.cpu.usage"),
        "NetworkSample": ("timeseries", "builtin:host.net.bytesTx"),
        "StorageSample": ("timeseries", "builtin:host.disk.usedPct"),
        "ContainerSample": ("timeseries", "builtin:containers.cpu.usagePercent"),

        # Browser/RUM Events
        "PageView": ("bizevents", None),
        "PageAction": ("bizevents", None),
        "BrowserInteraction": ("bizevents", None),
        "JavaScriptError": ("logs", None),
        "AjaxRequest": ("bizevents", None),

        # Mobile Events
        "Mobile": ("bizevents", None),
        "MobileSession": ("bizevents", None),
        "MobileCrash": ("logs", None),

        # Synthetic Events
        "SyntheticCheck": ("timeseries", "builtin:synthetic.http.duration.geo"),
        "SyntheticRequest": ("timeseries", "builtin:synthetic.http.duration.geo"),

        # Logs
        "Log": ("logs", None),

        # Custom Events
        "Metric": ("timeseries", None),
        "Custom": ("bizevents", None),
    }

    # =========================================================================
    # Aggregation Function Mappings
    # =========================================================================

    AGGREGATION_MAPPINGS = {
        "count": "count()",
        "sum": "sum",
        "average": "avg",
        "avg": "avg",
        "max": "max",
        "min": "min",
        "latest": "last",
        "earliest": "first",
        "uniqueCount": "countDistinct",
        "uniques": "collectDistinct",
        "percentage": "sum",  # Needs transformation
        "percentile": "percentile",
        "median": "median",
        "stddev": "stddev",
        "rate": "rate",
        "filter": "filter",  # Special handling
        "funnel": None,  # Not directly supported
        "histogram": None,  # Different approach in DQL
    }

    # =========================================================================
    # Operator Mappings
    # =========================================================================

    OPERATOR_MAPPINGS = {
        "=": "==",
        "!=": "!=",
        "<": "<",
        ">": ">",
        "<=": "<=",
        ">=": ">=",
        "LIKE": "matches",
        "NOT LIKE": "not matches",
        "IN": "in",
        "NOT IN": "not in",
        "IS NULL": "isNull",
        "IS NOT NULL": "isNotNull",
        "AND": "and",
        "OR": "or",
        "NOT": "not",
    }

    def __init__(self):
        self.warnings: List[str] = []
        self.manual_review: List[str] = []
        self.field_mappings_used: Dict[str, str] = {}

    def convert(self, nrql: str) -> ConversionResult:
        """
        Convert an NRQL query to DQL.

        Args:
            nrql: The NRQL query string

        Returns:
            ConversionResult with the converted DQL and metadata
        """
        self.warnings = []
        self.manual_review = []
        self.field_mappings_used = {}

        # Normalize the query
        nrql = self._normalize_query(nrql)

        # Parse NRQL components
        parsed = self._parse_nrql(nrql)

        # Determine query type
        query_type = self._determine_query_type(parsed)

        # Build DQL
        dql = self._build_dql(parsed, query_type)

        # Determine confidence
        confidence = self._calculate_confidence()

        return ConversionResult(
            original_nrql=nrql,
            converted_dql=dql,
            query_type=query_type,
            confidence=confidence,
            warnings=self.warnings.copy(),
            manual_review_needed=self.manual_review.copy(),
            field_mappings_used=self.field_mappings_used.copy()
        )

    def _normalize_query(self, nrql: str) -> str:
        """Normalize NRQL query for parsing."""
        # Remove extra whitespace
        nrql = " ".join(nrql.split())
        # Ensure consistent casing for keywords
        return nrql.strip()

    def _parse_nrql(self, nrql: str) -> Dict[str, Any]:
        """Parse NRQL into components."""
        parsed = {
            "select": [],
            "from": None,
            "where": None,
            "facet": None,
            "since": None,
            "until": None,
            "limit": None,
            "timeseries": None,
            "compare_with": None,
            "order_by": None,
        }

        # Extract SELECT clause
        select_match = re.search(
            r"SELECT\s+(.+?)\s+FROM",
            nrql,
            re.IGNORECASE
        )
        if select_match:
            parsed["select"] = self._parse_select(select_match.group(1))

        # Extract FROM clause
        from_match = re.search(
            r"FROM\s+(\w+)",
            nrql,
            re.IGNORECASE
        )
        if from_match:
            parsed["from"] = from_match.group(1)

        # Extract WHERE clause
        where_match = re.search(
            r"WHERE\s+(.+?)(?:FACET|SINCE|UNTIL|LIMIT|TIMESERIES|COMPARE|ORDER|$)",
            nrql,
            re.IGNORECASE
        )
        if where_match:
            parsed["where"] = where_match.group(1).strip()

        # Extract FACET clause
        facet_match = re.search(
            r"FACET\s+(.+?)(?:SINCE|UNTIL|LIMIT|TIMESERIES|COMPARE|ORDER|$)",
            nrql,
            re.IGNORECASE
        )
        if facet_match:
            parsed["facet"] = [f.strip() for f in facet_match.group(1).split(",")]

        # Extract SINCE clause
        since_match = re.search(
            r"SINCE\s+(.+?)(?:UNTIL|LIMIT|TIMESERIES|COMPARE|ORDER|$)",
            nrql,
            re.IGNORECASE
        )
        if since_match:
            parsed["since"] = since_match.group(1).strip()

        # Extract UNTIL clause
        until_match = re.search(
            r"UNTIL\s+(.+?)(?:LIMIT|TIMESERIES|COMPARE|ORDER|$)",
            nrql,
            re.IGNORECASE
        )
        if until_match:
            parsed["until"] = until_match.group(1).strip()

        # Extract LIMIT clause
        limit_match = re.search(
            r"LIMIT\s+(\d+)",
            nrql,
            re.IGNORECASE
        )
        if limit_match:
            parsed["limit"] = int(limit_match.group(1))

        # Extract TIMESERIES clause
        timeseries_match = re.search(
            r"TIMESERIES(?:\s+(\d+)\s+(\w+))?",
            nrql,
            re.IGNORECASE
        )
        if timeseries_match:
            if timeseries_match.group(1):
                parsed["timeseries"] = f"{timeseries_match.group(1)} {timeseries_match.group(2)}"
            else:
                parsed["timeseries"] = "AUTO"

        # Extract COMPARE WITH clause
        compare_match = re.search(
            r"COMPARE\s+WITH\s+(.+?)(?:LIMIT|ORDER|$)",
            nrql,
            re.IGNORECASE
        )
        if compare_match:
            parsed["compare_with"] = compare_match.group(1).strip()
            self.warnings.append("COMPARE WITH requires manual implementation in DQL")

        return parsed

    def _parse_select(self, select_clause: str) -> List[Dict[str, Any]]:
        """Parse SELECT clause into individual selections."""
        selections = []

        # Handle * (select all)
        if select_clause.strip() == "*":
            return [{"type": "all", "expression": "*"}]

        # Parse individual selections (handle nested parentheses)
        parts = self._split_select_parts(select_clause)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            selection = {"type": "expression", "expression": part}

            # Check for aggregation functions
            agg_match = re.match(
                r"(\w+)\s*\(\s*(.+?)\s*\)(?:\s+AS\s+['\"]?(\w+)['\"]?)?",
                part,
                re.IGNORECASE
            )
            if agg_match:
                func_name = agg_match.group(1).lower()
                field = agg_match.group(2)
                alias = agg_match.group(3)

                selection = {
                    "type": "aggregation",
                    "function": func_name,
                    "field": field,
                    "alias": alias,
                    "expression": part
                }

            selections.append(selection)

        return selections

    def _split_select_parts(self, select_clause: str) -> List[str]:
        """Split SELECT clause respecting parentheses."""
        parts = []
        current = ""
        depth = 0

        for char in select_clause:
            if char == "(":
                depth += 1
                current += char
            elif char == ")":
                depth -= 1
                current += char
            elif char == "," and depth == 0:
                parts.append(current)
                current = ""
            else:
                current += char

        if current:
            parts.append(current)

        return parts

    def _determine_query_type(self, parsed: Dict[str, Any]) -> QueryType:
        """Determine the type of query based on FROM clause."""
        from_clause = parsed.get("from", "").lower()

        if from_clause in ["log", "logs"]:
            return QueryType.LOGS
        elif from_clause in ["span", "spans", "distributedtrace"]:
            return QueryType.TRACES
        elif from_clause in ["metric", "metrics"]:
            return QueryType.METRICS
        elif from_clause in self.EVENT_TYPE_MAPPINGS:
            mapping = self.EVENT_TYPE_MAPPINGS[from_clause]
            if mapping[0] == "logs":
                return QueryType.LOGS
            elif mapping[0] == "spans":
                return QueryType.TRACES
            else:
                return QueryType.METRICS
        else:
            return QueryType.EVENTS

    def _build_dql(self, parsed: Dict[str, Any], query_type: QueryType) -> str:
        """Build DQL query from parsed NRQL."""
        dql_parts = []

        # Determine fetch statement
        fetch_statement = self._build_fetch(parsed, query_type)
        dql_parts.append(fetch_statement)

        # Add filter (WHERE)
        if parsed.get("where"):
            filter_clause = self._convert_where(parsed["where"])
            dql_parts.append(f"| filter {filter_clause}")

        # Add summarize/fieldsAdd for aggregations
        aggregation_clause = self._build_aggregations(parsed)
        if aggregation_clause:
            dql_parts.append(aggregation_clause)

        # Add group by (FACET)
        if parsed.get("facet"):
            facet_fields = [self._map_field(f) for f in parsed["facet"]]
            # In DQL, grouping is part of summarize
            if "summarize" not in dql_parts[-1]:
                dql_parts.append(f"| summarize by: {{{', '.join(facet_fields)}}}")

        # Add sort (ORDER BY)
        if parsed.get("order_by"):
            dql_parts.append(f"| sort {parsed['order_by']}")

        # Add limit
        if parsed.get("limit"):
            dql_parts.append(f"| limit {parsed['limit']}")

        return "\n".join(dql_parts)

    def _build_fetch(self, parsed: Dict[str, Any], query_type: QueryType) -> str:
        """Build the fetch statement."""
        from_clause = parsed.get("from", "")

        # Get time range
        time_range = self._convert_time_range(parsed)

        # Determine data source
        if query_type == QueryType.LOGS:
            fetch = f"fetch logs{time_range}"
        elif query_type == QueryType.TRACES:
            fetch = f"fetch spans{time_range}"
        elif query_type == QueryType.METRICS:
            # Check if we have a specific metric mapping
            if from_clause in self.EVENT_TYPE_MAPPINGS:
                mapping = self.EVENT_TYPE_MAPPINGS[from_clause]
                if mapping[1]:
                    fetch = f"timeseries {mapping[1]}{time_range}"
                else:
                    fetch = f"fetch dt.entity.service{time_range}"
            else:
                fetch = f"fetch dt.entity.service{time_range}"
        else:
            # Business events or custom
            fetch = f"fetch bizevents{time_range}"
            self.warnings.append(f"Event type '{from_clause}' mapped to bizevents - verify this is correct")

        return fetch

    def _convert_time_range(self, parsed: Dict[str, Any]) -> str:
        """Convert NRQL time range to DQL."""
        since = parsed.get("since", "")

        if not since:
            return ""

        since_lower = since.lower()

        # Convert common patterns
        time_mappings = {
            "1 hour ago": ", from:now()-1h",
            "1 hours ago": ", from:now()-1h",
            "2 hours ago": ", from:now()-2h",
            "3 hours ago": ", from:now()-3h",
            "6 hours ago": ", from:now()-6h",
            "12 hours ago": ", from:now()-12h",
            "24 hours ago": ", from:now()-24h",
            "1 day ago": ", from:now()-1d",
            "2 days ago": ", from:now()-2d",
            "7 days ago": ", from:now()-7d",
            "1 week ago": ", from:now()-7d",
            "30 days ago": ", from:now()-30d",
            "1 month ago": ", from:now()-30d",
        }

        for nrql_time, dql_time in time_mappings.items():
            if nrql_time in since_lower:
                return dql_time

        # Try to parse numeric patterns
        time_match = re.match(r"(\d+)\s+(minute|hour|day|week|month)s?\s+ago", since_lower)
        if time_match:
            value = time_match.group(1)
            unit = time_match.group(2)[0]  # First letter: m, h, d, w, m
            if unit == "w":
                value = str(int(value) * 7)
                unit = "d"
            elif unit == "m" and time_match.group(2) == "month":
                value = str(int(value) * 30)
                unit = "d"
            return f", from:now()-{value}{unit}"

        self.warnings.append(f"Could not convert time range: {since}")
        return ""

    def _convert_where(self, where_clause: str) -> str:
        """Convert NRQL WHERE clause to DQL filter."""
        result = where_clause

        # Map fields
        for nrql_field, dql_field in self.FIELD_MAPPINGS.items():
            pattern = rf"\b{re.escape(nrql_field)}\b"
            if re.search(pattern, result, re.IGNORECASE):
                result = re.sub(pattern, dql_field, result, flags=re.IGNORECASE)
                self.field_mappings_used[nrql_field] = dql_field

        # Convert operators
        result = re.sub(r"\s*=\s*", " == ", result)
        result = re.sub(r"\bAND\b", "and", result, flags=re.IGNORECASE)
        result = re.sub(r"\bOR\b", "or", result, flags=re.IGNORECASE)
        result = re.sub(r"\bNOT\b", "not", result, flags=re.IGNORECASE)

        # Convert LIKE to matches (basic conversion)
        like_pattern = r"(\w+(?:\.\w+)*)\s+LIKE\s+'([^']+)'"
        like_matches = re.findall(like_pattern, result, re.IGNORECASE)
        for field, pattern in like_matches:
            # Convert SQL wildcards to regex
            regex_pattern = pattern.replace("%", ".*").replace("_", ".")
            result = re.sub(
                rf"{re.escape(field)}\s+LIKE\s+'{re.escape(pattern)}'",
                f'matchesPhrase({field}, "{regex_pattern}")',
                result,
                flags=re.IGNORECASE
            )

        # Convert IN clause
        in_pattern = r"(\w+(?:\.\w+)*)\s+IN\s*\(([^)]+)\)"
        result = re.sub(in_pattern, r"in(\1, \2)", result, flags=re.IGNORECASE)

        # Convert IS NULL / IS NOT NULL
        result = re.sub(r"(\w+)\s+IS\s+NULL", r"isNull(\1)", result, flags=re.IGNORECASE)
        result = re.sub(r"(\w+)\s+IS\s+NOT\s+NULL", r"isNotNull(\1)", result, flags=re.IGNORECASE)

        return result.strip()

    def _build_aggregations(self, parsed: Dict[str, Any]) -> str:
        """Build aggregation statements from SELECT."""
        selections = parsed.get("select", [])

        if not selections:
            return ""

        # Check if we have aggregations
        aggregations = [s for s in selections if s.get("type") == "aggregation"]

        if not aggregations:
            return ""

        agg_parts = []

        for agg in aggregations:
            func = agg["function"]
            field = agg["field"]
            alias = agg.get("alias")

            # Map field
            mapped_field = self._map_field(field)

            # Map function
            dql_func = self.AGGREGATION_MAPPINGS.get(func.lower())

            if dql_func is None:
                self.manual_review.append(f"Aggregation '{func}' needs manual conversion")
                dql_func = func

            if dql_func == "count()":
                agg_expr = "count()"
            elif func.lower() == "percentile":
                # Handle percentile(field, 95) syntax
                percentile_match = re.match(r"(.+?),\s*(\d+)", field)
                if percentile_match:
                    pct_field = self._map_field(percentile_match.group(1))
                    pct_value = percentile_match.group(2)
                    agg_expr = f"percentile({pct_field}, {pct_value})"
                else:
                    agg_expr = f"percentile({mapped_field}, 95)"
            else:
                agg_expr = f"{dql_func}({mapped_field})"

            if alias:
                agg_expr = f"{alias} = {agg_expr}"

            agg_parts.append(agg_expr)

        # Add facet grouping if present
        facet = parsed.get("facet")
        if facet:
            facet_fields = [self._map_field(f) for f in facet]
            return f"| summarize {', '.join(agg_parts)}, by: {{{', '.join(facet_fields)}}}"
        else:
            return f"| summarize {', '.join(agg_parts)}"

    def _map_field(self, field: str) -> str:
        """Map a field name from NRQL to DQL."""
        field = field.strip()

        # Check direct mapping
        if field in self.FIELD_MAPPINGS:
            self.field_mappings_used[field] = self.FIELD_MAPPINGS[field]
            return self.FIELD_MAPPINGS[field]

        # Check case-insensitive
        field_lower = field.lower()
        for nrql_field, dql_field in self.FIELD_MAPPINGS.items():
            if nrql_field.lower() == field_lower:
                self.field_mappings_used[field] = dql_field
                return dql_field

        # No mapping found, return as-is
        return field

    def _calculate_confidence(self) -> str:
        """Calculate confidence level of the conversion."""
        if len(self.manual_review) > 0:
            return "low"
        elif len(self.warnings) > 2:
            return "low"
        elif len(self.warnings) > 0:
            return "medium"
        else:
            return "high"


# =============================================================================
# Reference Tables
# =============================================================================

NRQL_DQL_REFERENCE = """
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                        NRQL to DQL Quick Reference                                  ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ NRQL                                    │ DQL                                       ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ SELECT * FROM Log                       │ fetch logs                                ┃
┃ SELECT count(*) FROM Transaction        │ fetch ... | summarize count()             ┃
┃ WHERE field = 'value'                   │ | filter field == "value"                 ┃
┃ WHERE field LIKE '%pattern%'            │ | filter matchesPhrase(field, "pattern")  ┃
┃ WHERE field IN ('a', 'b')               │ | filter in(field, "a", "b")              ┃
┃ WHERE field IS NULL                     │ | filter isNull(field)                    ┃
┃ FACET fieldName                         │ | summarize by: {fieldName}               ┃
┃ SINCE 1 hour ago                        │ from:now()-1h                             ┃
┃ LIMIT 100                               │ | limit 100                               ┃
┃ TIMESERIES                              │ | timeseries                              ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ AGGREGATIONS                            │                                           ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ count(*)                                │ count()                                   ┃
┃ average(field)                          │ avg(field)                                ┃
┃ sum(field)                              │ sum(field)                                ┃
┃ max(field)                              │ max(field)                                ┃
┃ min(field)                              │ min(field)                                ┃
┃ uniqueCount(field)                      │ countDistinct(field)                      ┃
┃ percentile(field, 95)                   │ percentile(field, 95)                     ┃
┃ latest(field)                           │ last(field)                               ┃
┃ earliest(field)                         │ first(field)                              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""


def print_reference_table():
    """Print the NRQL to DQL reference table."""
    table = Table(title="NRQL to DQL Quick Reference", show_header=True, header_style="bold cyan")
    table.add_column("NRQL", style="green")
    table.add_column("DQL", style="blue")

    references = [
        ("SELECT * FROM Log", "fetch logs"),
        ("SELECT count(*) FROM Transaction", "fetch ... | summarize count()"),
        ("WHERE field = 'value'", '| filter field == "value"'),
        ("WHERE field LIKE '%pattern%'", '| filter matchesPhrase(field, "pattern")'),
        ("WHERE field IN ('a', 'b')", '| filter in(field, "a", "b")'),
        ("WHERE field IS NULL", "| filter isNull(field)"),
        ("FACET fieldName", "| summarize by: {fieldName}"),
        ("SINCE 1 hour ago", "from:now()-1h"),
        ("LIMIT 100", "| limit 100"),
        ("TIMESERIES", "| timeseries"),
        ("─" * 35, "─" * 35),
        ("count(*)", "count()"),
        ("average(field)", "avg(field)"),
        ("sum(field)", "sum(field)"),
        ("max(field)", "max(field)"),
        ("min(field)", "min(field)"),
        ("uniqueCount(field)", "countDistinct(field)"),
        ("percentile(field, 95)", "percentile(field, 95)"),
        ("latest(field)", "last(field)"),
        ("earliest(field)", "first(field)"),
    ]

    for nrql, dql in references:
        table.add_row(nrql, dql)

    console.print(table)


def display_result(result: ConversionResult):
    """Display conversion result with rich formatting."""
    # Original NRQL
    console.print("\n[bold cyan]Original NRQL:[/bold cyan]")
    console.print(Panel(result.original_nrql, border_style="cyan"))

    # Converted DQL
    confidence_color = {"high": "green", "medium": "yellow", "low": "red"}[result.confidence]
    console.print(f"\n[bold green]Converted DQL[/bold green] [dim](confidence: [{confidence_color}]{result.confidence}[/{confidence_color}])[/dim]:")
    console.print(Panel(
        Syntax(result.converted_dql, "sql", theme="monokai"),
        border_style="green"
    ))

    # Field mappings used
    if result.field_mappings_used:
        console.print("\n[bold blue]Field Mappings Applied:[/bold blue]")
        for nrql_field, dql_field in result.field_mappings_used.items():
            console.print(f"  • {nrql_field} → {dql_field}")

    # Warnings
    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in result.warnings:
            console.print(f"  ⚠ {warning}")

    # Manual review items
    if result.manual_review_needed:
        console.print("\n[bold red]Manual Review Required:[/bold red]")
        for item in result.manual_review_needed:
            console.print(f"  ✗ {item}")


# =============================================================================
# CLI Commands
# =============================================================================

@click.command()
@click.argument("query", required=False)
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--file", "-f", type=click.Path(exists=True), help="Read queries from file")
@click.option("--reference", "-r", is_flag=True, help="Show reference table")
@click.option("--output", "-o", type=click.Path(), help="Output file for converted queries")
def main(query: Optional[str], interactive: bool, file: Optional[str], reference: bool, output: Optional[str]):
    """
    NRQL to DQL Converter

    Convert New Relic Query Language (NRQL) queries to Dynatrace Query Language (DQL).

    Examples:

        python nrql_to_dql.py "SELECT count(*) FROM Transaction"

        python nrql_to_dql.py --interactive

        python nrql_to_dql.py --reference
    """
    converter = NRQLtoDQLConverter()

    if reference:
        print_reference_table()
        return

    if interactive:
        console.print("[bold]NRQL to DQL Converter - Interactive Mode[/bold]")
        console.print("Enter NRQL queries (type 'quit' to exit, 'ref' for reference)\n")

        while True:
            try:
                nrql_input = console.input("[cyan]NRQL>[/cyan] ")

                if nrql_input.lower() in ("quit", "exit", "q"):
                    break

                if nrql_input.lower() in ("ref", "reference", "help"):
                    print_reference_table()
                    continue

                if not nrql_input.strip():
                    continue

                result = converter.convert(nrql_input)
                display_result(result)
                console.print()

            except KeyboardInterrupt:
                console.print("\n[yellow]Exiting...[/yellow]")
                break

        return

    if file:
        with open(file, "r") as f:
            queries = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        results = []
        for q in queries:
            result = converter.convert(q)
            results.append(result)
            display_result(result)
            console.print("─" * 60)

        if output:
            with open(output, "w") as f:
                for result in results:
                    f.write(f"-- Original: {result.original_nrql}\n")
                    f.write(f"{result.converted_dql}\n\n")
            console.print(f"[green]Results saved to {output}[/green]")

        return

    if query:
        result = converter.convert(query)
        display_result(result)

        if output:
            with open(output, "w") as f:
                f.write(f"-- Original: {result.original_nrql}\n")
                f.write(f"{result.converted_dql}\n")
            console.print(f"\n[green]Result saved to {output}[/green]")

        return

    # No arguments - show help
    ctx = click.get_current_context()
    click.echo(ctx.get_help())


if __name__ == "__main__":
    main()

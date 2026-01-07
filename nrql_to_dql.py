#!/usr/bin/env python3
"""
NRQL to DQL Converter
Converts NewRelic Query Language (NRQL) queries to Dynatrace Query Language (DQL).
"""

import re
import sys
import argparse
from typing import Dict, Optional, Tuple


class NRQLtoDQLConverter:
    """Converter class for transforming NRQL queries to DQL."""
    
    def __init__(self):
        """Initialize the converter with mapping dictionaries."""
        # Function mappings from NRQL to DQL
        self.function_mappings = {
            'count': 'count',
            'sum': 'sum',
            'average': 'avg',
            'avg': 'avg',
            'min': 'min',
            'max': 'max',
            'uniquecount': 'countDistinct',
            'percentage': 'percentage',
            'rate': 'rate',
            'stddev': 'stddev',
            'median': 'median',
            'percentile': 'percentile',
        }
        
        # Time range mappings
        self.time_mappings = {
            'minutes': 'm',
            'minute': 'm',
            'hours': 'h',
            'hour': 'h',
            'days': 'd',
            'day': 'd',
            'weeks': 'w',
            'week': 'w',
        }
        
    def convert(self, nrql_query: str) -> str:
        """
        Convert an NRQL query to DQL.
        
        Args:
            nrql_query: The NRQL query string to convert
            
        Returns:
            The converted DQL query string
        """
        query = nrql_query.strip()
        
        # Parse the query into components
        select_clause = self._extract_select_clause(query)
        from_clause = self._extract_from_clause(query)
        where_clause = self._extract_where_clause(query)
        since_clause = self._extract_since_clause(query)
        facet_clause = self._extract_facet_clause(query)
        limit_clause = self._extract_limit_clause(query)
        
        # Build DQL query
        dql_parts = []
        
        # FROM clause comes first in DQL
        if from_clause:
            dql_parts.append(f"fetch {from_clause}")
        
        # WHERE/FILTER clause
        if where_clause:
            dql_parts.append(f"| filter {where_clause}")
        
        # Time range (timeframe)
        if since_clause:
            dql_parts.append(f"| filterTime {since_clause}")
        
        # SELECT becomes fields or summarize in DQL
        if select_clause:
            select_dql = self._convert_select_to_dql(select_clause, facet_clause)
            if select_dql:
                dql_parts.append(select_dql)
        
        # LIMIT clause
        if limit_clause:
            dql_parts.append(f"| limit {limit_clause}")
        
        dql_query = ' '.join(dql_parts)
        return dql_query
    
    def _extract_select_clause(self, query: str) -> Optional[str]:
        """Extract the SELECT clause from NRQL query."""
        match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_from_clause(self, query: str) -> Optional[str]:
        """Extract and convert the FROM clause."""
        match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        if match:
            # Convert NewRelic event types to DQL record types
            event_type = match.group(1)
            # Common mappings
            type_mappings = {
                'Transaction': 'dt.entity.process_group_instance',
                'TransactionError': 'dt.entity.process_group_instance',
                'Metric': 'dt.metrics',
                'Log': 'dt.entity.log',
                'SystemSample': 'dt.entity.host',
                'ProcessSample': 'dt.entity.process',
            }
            return type_mappings.get(event_type, f"dt.entity.{event_type.lower()}")
        return None
    
    def _extract_where_clause(self, query: str) -> Optional[str]:
        """Extract and convert the WHERE clause."""
        # Match WHERE clause, stopping at SINCE, FACET, LIMIT, or end
        match = re.search(r'WHERE\s+(.*?)(?:\s+(?:SINCE|FACET|LIMIT|$))', query, re.IGNORECASE | re.DOTALL)
        if match:
            where_content = match.group(1).strip()
            # Convert NRQL WHERE syntax to DQL filter syntax
            where_content = self._convert_where_conditions(where_content)
            return where_content
        return None
    
    def _convert_where_conditions(self, where_clause: str) -> str:
        """Convert WHERE conditions from NRQL to DQL syntax."""
        # Convert LIKE to contains, startsWith, or endsWith
        # Order matters: check most specific patterns first
        where_clause = re.sub(r"(\w+)\s+LIKE\s+'%(.+?)%'", r"contains(\1, '\2')", where_clause, flags=re.IGNORECASE)
        where_clause = re.sub(r"(\w+)\s+LIKE\s+'(.+?)%'", r"startsWith(\1, '\2')", where_clause, flags=re.IGNORECASE)
        where_clause = re.sub(r"(\w+)\s+LIKE\s+'%(.+?)'", r"endsWith(\1, '\2')", where_clause, flags=re.IGNORECASE)
        
        # Convert = to ==
        where_clause = re.sub(r"(\w+)\s*=\s*'([^']+)'", r"\1 == '\2'", where_clause)
        where_clause = re.sub(r"(\w+)\s*=\s*(\d+)", r"\1 == \2", where_clause)
        
        # Convert AND/OR (DQL uses 'and'/'or' lowercase)
        where_clause = re.sub(r'\bAND\b', 'and', where_clause, flags=re.IGNORECASE)
        where_clause = re.sub(r'\bOR\b', 'or', where_clause, flags=re.IGNORECASE)
        where_clause = re.sub(r'\bNOT\b', 'not', where_clause, flags=re.IGNORECASE)
        
        return where_clause
    
    def _extract_since_clause(self, query: str) -> Optional[str]:
        """Extract and convert the SINCE clause."""
        match = re.search(r'SINCE\s+(\d+)\s+(\w+)\s+ago', query, re.IGNORECASE)
        if match:
            value = match.group(1)
            unit = match.group(2).lower()
            dql_unit = self.time_mappings.get(unit, unit)
            return f"-{value}{dql_unit}"
        
        # Check for UNTIL clause as well
        match = re.search(r'SINCE\s+(\d+)\s+(\w+)\s+ago\s+UNTIL\s+(\d+)\s+(\w+)\s+ago', query, re.IGNORECASE)
        if match:
            since_value = match.group(1)
            since_unit = match.group(2).lower()
            until_value = match.group(3)
            until_unit = match.group(4).lower()
            since_dql = self.time_mappings.get(since_unit, since_unit)
            until_dql = self.time_mappings.get(until_unit, until_unit)
            return f"from:-{since_value}{since_dql}, to:-{until_value}{until_dql}"
        
        return None
    
    def _extract_facet_clause(self, query: str) -> Optional[str]:
        """Extract the FACET (GROUP BY) clause."""
        match = re.search(r'FACET\s+(.*?)(?:\s+(?:WHERE|SINCE|LIMIT|$))', query, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_limit_clause(self, query: str) -> Optional[str]:
        """Extract the LIMIT clause."""
        match = re.search(r'LIMIT\s+(\d+)', query, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _convert_select_to_dql(self, select_clause: str, facet_clause: Optional[str] = None) -> str:
        """Convert SELECT clause to DQL fields or summarize."""
        # Check if this is an aggregation query
        has_aggregation = any(func in select_clause.lower() for func in self.function_mappings.keys())
        
        if has_aggregation or facet_clause:
            # This needs a summarize operation
            return self._build_summarize_clause(select_clause, facet_clause)
        else:
            # Simple field selection
            if select_clause.strip() == '*':
                return ""  # No need for fields clause with *
            else:
                fields = [f.strip() for f in select_clause.split(',')]
                return f"| fields {', '.join(fields)}"
    
    def _build_summarize_clause(self, select_clause: str, facet_clause: Optional[str]) -> str:
        """Build a DQL summarize clause from NRQL aggregation."""
        # Parse aggregation functions
        aggregations = []
        
        # Match patterns like COUNT(*), AVG(duration), SUM(amount), etc.
        agg_pattern = r'(\w+)\s*\(\s*([^)]*)\s*\)(?:\s+as\s+(\w+))?'
        matches = re.finditer(agg_pattern, select_clause, re.IGNORECASE)
        
        for match in matches:
            func = match.group(1).lower()
            field = match.group(2).strip() if match.group(2).strip() else '*'
            alias = match.group(3) if match.group(3) else None
            
            dql_func = self.function_mappings.get(func, func)
            
            if field == '*':
                agg_str = f"{dql_func}()"
            else:
                agg_str = f"{dql_func}({field})"
            
            if alias:
                agg_str = f"{alias} = {agg_str}"
            
            aggregations.append(agg_str)
        
        # If no aggregations found, might be a simple field in a facet query
        if not aggregations:
            aggregations.append("count()")
        
        summarize_parts = [f"| summarize {', '.join(aggregations)}"]
        
        if facet_clause:
            # Add by clause for faceting
            facet_fields = [f.strip() for f in facet_clause.split(',')]
            summarize_parts.append(f"by {', '.join(facet_fields)}")
        
        return ' '.join(summarize_parts)


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(
        description='Convert NewRelic NRQL queries to Dynatrace DQL queries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nrql_to_dql.py "SELECT count(*) FROM Transaction WHERE appName = 'MyApp' SINCE 1 hour ago"
  nrql_to_dql.py "SELECT average(duration) FROM Transaction FACET name SINCE 24 hours ago LIMIT 10"
  nrql_to_dql.py --file input.nrql --output output.dql
        """
    )
    
    parser.add_argument('query', nargs='?', help='NRQL query to convert')
    parser.add_argument('-f', '--file', help='Input file containing NRQL query')
    parser.add_argument('-o', '--output', help='Output file for DQL query')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Get input query
    if args.file:
        try:
            with open(args.file, 'r') as f:
                nrql_query = f.read().strip()
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.query:
        nrql_query = args.query
    else:
        parser.print_help()
        sys.exit(1)
    
    # Convert query
    converter = NRQLtoDQLConverter()
    
    if args.verbose:
        print(f"Input NRQL: {nrql_query}")
        print()
    
    try:
        dql_query = converter.convert(nrql_query)
        
        if args.verbose:
            print(f"Output DQL: {dql_query}")
        else:
            print(dql_query)
        
        # Write to output file if specified
        if args.output:
            with open(args.output, 'w') as f:
                f.write(dql_query)
                f.write('\n')
            if args.verbose:
                print(f"\nOutput written to: {args.output}")
    
    except Exception as e:
        print(f"Error converting query: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

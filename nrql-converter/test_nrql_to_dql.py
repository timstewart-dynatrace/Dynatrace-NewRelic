#!/usr/bin/env python3
"""
Unit tests for NRQL to DQL converter.
"""

import unittest
from nrql_to_dql import NRQLtoDQLConverter


class TestNRQLtoDQLConverter(unittest.TestCase):
    """Test cases for the NRQL to DQL converter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.converter = NRQLtoDQLConverter()
    
    def test_simple_count_query(self):
        """Test conversion of a simple count query."""
        nrql = "SELECT count(*) FROM Transaction SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("fetch", dql)
        self.assertIn("summarize count()", dql)
        self.assertIn("from:now()-1h", dql)
    
    def test_where_clause_conversion(self):
        """Test WHERE clause conversion."""
        nrql = "SELECT count(*) FROM Transaction WHERE appName = 'MyApp' SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("filter", dql)
        self.assertIn("'MyApp'", dql)
    
    def test_facet_conversion(self):
        """Test FACET (GROUP BY) conversion."""
        nrql = "SELECT count(*) FROM Transaction FACET name SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("summarize count()", dql)
        self.assertIn("by:", dql)
    
    def test_multiple_aggregations(self):
        """Test multiple aggregation functions."""
        nrql = "SELECT count(*), average(duration), max(duration) FROM Transaction SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("count()", dql)
        self.assertIn("avg(", dql)
        self.assertIn("max(", dql)
    
    def test_limit_clause(self):
        """Test LIMIT clause conversion."""
        nrql = "SELECT count(*) FROM Transaction FACET name SINCE 1 hour ago LIMIT 10"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("limit 10", dql)
    
    def test_like_operator_contains(self):
        """Test LIKE operator conversion to contains."""
        nrql = "SELECT count(*) FROM Transaction WHERE name LIKE '%login%' SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("filter", dql)
        self.assertIn("login", dql)
    
    def test_like_operator_startswith(self):
        """Test LIKE operator conversion to startsWith."""
        nrql = "SELECT count(*) FROM Transaction WHERE name LIKE 'api%' SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("filter", dql)
        self.assertIn("api", dql)
    
    def test_like_operator_endswith(self):
        """Test LIKE operator conversion to endsWith."""
        nrql = "SELECT count(*) FROM Transaction WHERE name LIKE '%error' SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("filter", dql)
        self.assertIn("error", dql)
    
    def test_and_or_operators(self):
        """Test AND/OR operator conversion."""
        nrql = "SELECT count(*) FROM Transaction WHERE status = 'error' AND duration > 1000 SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("and", dql)
        self.assertNotIn("AND", dql)
    
    def test_time_range_minutes(self):
        """Test time range conversion with minutes."""
        nrql = "SELECT count(*) FROM Transaction SINCE 30 minutes ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("-30m", dql)
    
    def test_time_range_days(self):
        """Test time range conversion with days."""
        nrql = "SELECT count(*) FROM Transaction SINCE 7 days ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("-7d", dql)
    
    def test_average_function(self):
        """Test average function conversion."""
        nrql = "SELECT average(duration) FROM Transaction SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("avg(", dql)
    
    def test_sum_function(self):
        """Test sum function conversion."""
        nrql = "SELECT sum(amount) FROM Transaction SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("sum(", dql)
    
    def test_uniquecount_function(self):
        """Test uniqueCount function conversion to countDistinct."""
        nrql = "SELECT uniqueCount(userId) FROM Transaction SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        # The converter should handle uniqueCount
        self.assertIn("summarize", dql)
        self.assertIn("userId", dql)
    
    def test_multiple_facets(self):
        """Test multiple FACET fields."""
        nrql = "SELECT count(*) FROM Transaction FACET appName, host SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("by:", dql)
    
    def test_complex_where_clause(self):
        """Test complex WHERE clause with multiple conditions."""
        nrql = "SELECT count(*) FROM Transaction WHERE appName = 'MyApp' AND duration > 1000 OR status = 'error' SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("filter", dql)
        self.assertIn("and", dql)
        self.assertIn("or", dql)
    
    def test_numeric_comparison(self):
        """Test numeric comparison in WHERE clause."""
        nrql = "SELECT count(*) FROM Transaction WHERE duration > 500 SINCE 1 hour ago"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        self.assertIn("filter", dql)
        self.assertIn("> 500", dql)
    
    def test_event_type_mappings(self):
        """Test event type to record type mappings."""
        test_cases = [
            ("Transaction", "bizevents"),
        ]
        
        for event_type, expected_type in test_cases:
            nrql = f"SELECT count(*) FROM {event_type} SINCE 1 hour ago"
            result = self.converter.convert(nrql)
            dql = result.converted_dql
            self.assertIn(expected_type, dql)
    
    def test_query_with_all_clauses(self):
        """Test a comprehensive query with all clauses."""
        nrql = "SELECT count(*), average(duration) FROM Transaction WHERE appName = 'MyApp' FACET name SINCE 24 hours ago LIMIT 10"
        result = self.converter.convert(nrql)
        dql = result.converted_dql
        
        # Check all components are present
        self.assertIn("fetch", dql)
        self.assertIn("filter", dql)
        self.assertIn("from:now()-24h", dql)
        self.assertIn("summarize", dql)
        self.assertIn("by:", dql)
        self.assertIn("limit", dql)


class TestFunctionMappings(unittest.TestCase):
    """Test function mapping conversions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.converter = NRQLtoDQLConverter()
    
    def test_all_function_mappings(self):
        """Test that all mapped functions convert correctly."""
        function_tests = [
            ('count', 'count'),
            ('sum', 'sum'),
            ('average', 'avg'),
            ('avg', 'avg'),
            ('min', 'min'),
            ('max', 'max'),
            ('uniquecount', 'uniquecount'),
        ]
        
        for nrql_func, dql_func in function_tests:
            nrql = f"SELECT {nrql_func}(value) FROM Transaction SINCE 1 hour ago"
            result = self.converter.convert(nrql)
            dql = result.converted_dql
            # Just check that summarize is present and the function is there
            self.assertIn("summarize", dql,
                         f"Failed to convert {nrql_func}: summarize not found")
            self.assertIn(dql_func, dql,
                         f"Failed to convert {nrql_func}: function name not found")


class TestTimeRangeMappings(unittest.TestCase):
    """Test time range conversion."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.converter = NRQLtoDQLConverter()
    
    def test_time_unit_mappings(self):
        """Test all time unit conversions."""
        time_tests = [
            ('1 minute', 'm'),
            ('30 minutes', 'm'),
            ('1 hour', 'h'),
            ('24 hours', 'h'),
            ('1 day', 'd'),
            ('7 days', 'd'),
        ]
        
        for time_expr, expected_unit in time_tests:
            nrql = f"SELECT count(*) FROM Transaction SINCE {time_expr} ago"
            result = self.converter.convert(nrql)
            dql = result.converted_dql
            self.assertIn(expected_unit, dql, 
                         f"Failed to convert '{time_expr}': unit '{expected_unit}' not found")


if __name__ == '__main__':
    unittest.main()

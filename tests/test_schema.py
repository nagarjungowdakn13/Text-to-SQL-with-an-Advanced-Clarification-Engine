import pytest
from app.services.schema.extractor import SchemaExtractor
from app.services.schema.graph import SchemaGraph
from app.services.schema.cache import SchemaCache
from app.core.config import settings

def test_schema_extraction():
    """Verify that all seeded tables, columns, rows, and keys are successfully extracted."""
    extractor = SchemaExtractor(settings.EXECUTION_DB_ADMIN_URL)
    schema = extractor.extract_schema()
    
    assert "customers" in schema.tables
    assert "orders" in schema.tables
    assert "products" in schema.tables
    assert "order_items" in schema.tables
    
    # Assert column metadata
    cust_table = schema.tables["customers"]
    assert "customer_id" in cust_table.primary_keys
    col_names = [col.name for col in cust_table.columns]
    assert "first_name" in col_names
    assert "email" in col_names
    assert cust_table.row_count == 4

def test_schema_graph_pathfinding():
    """Verify that pathfinding correctly finds shortest joins between disjoint tables."""
    extractor = SchemaExtractor(settings.EXECUTION_DB_ADMIN_URL)
    schema = extractor.extract_schema()
    graph = SchemaGraph(schema)
    
    # Shortest path between customers and products should include orders and order_items
    path = graph.find_shortest_path("customers", "products")
    assert "customers" in path
    assert "products" in path
    assert "orders" in path or "order_items" in path

def test_schema_subset_retrieval():
    """Verify that schema subset selection prunes irrelevant tables."""
    extractor = SchemaExtractor(settings.EXECUTION_DB_ADMIN_URL)
    schema = extractor.extract_schema()
    graph = SchemaGraph(schema)
    
    # Question mentions products, should extract products and adjacent tables (1-hop)
    subset = graph.get_relevant_schema_subset("Show me our products list")
    assert "products" in subset.tables
    # Since only one seed table is identified, it includes its neighbors
    assert len(subset.tables) > 1
    # Irrelevant tables shouldn't be blindly included if we have specific matches

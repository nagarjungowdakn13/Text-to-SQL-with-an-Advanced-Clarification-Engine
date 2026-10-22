from typing import List, Dict, Set, Any
from collections import deque
from app.services.schema.extractor import DatabaseSchemaMetadata, TableMetadata
from app.core.logging import logger

class SchemaGraph:
    def __init__(self, schema: DatabaseSchemaMetadata):
        self.schema = schema
        self.graph: Dict[str, Set[str]] = {}
        self._build_graph()

    def _build_graph(self):
        """Build an adjacency list representation of table relationships."""
        for table_name in self.schema.tables:
            if table_name not in self.graph:
                self.graph[table_name] = set()
            
        for table_name, table in self.schema.tables.items():
            for fk in table.foreign_keys:
                ref_table = fk.referred_table
                if ref_table in self.schema.tables:
                    # Undirected graph for pathfinding joins
                    self.graph[table_name].add(ref_table)
                    self.graph[ref_table].add(table_name)
        
        logger.debug(f"SchemaGraph built with {len(self.graph)} tables.")

    def find_shortest_path(self, start: str, end: str) -> List[str]:
        """Find the shortest path of tables between start and end using BFS."""
        if start == end:
            return [start]
        if start not in self.graph or end not in self.graph:
            return []

        queue = deque([[start]])
        visited = {start}

        while queue:
            path = queue.popleft()
            node = path[-1]

            if node == end:
                return path

            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)
        return []

    def identify_seed_tables(self, question: str) -> Set[str]:
        """
        Identify tables directly referenced or semantically relevant to the question.
        Uses basic keyword matching and table comments analysis.
        """
        question_lower = question.lower()
        seed_tables = set()

        for table_name, table in self.schema.tables.items():
            # Check direct table name matches
            if table_name.lower() in question_lower or table_name.rstrip('s').lower() in question_lower:
                seed_tables.add(table_name)
                continue

            # Check column name matches (e.g. if 'email' is asked, the user might need 'customers' or 'users')
            for col in table.columns:
                col_word = f" {col.name.lower()} "
                if col_word in f" {question_lower} " or col.name.lower() == question_lower.strip():
                    seed_tables.add(table_name)
                    
            # Check comment matches
            if table.comment and any(word in question_lower for word in table.comment.lower().split()):
                seed_tables.add(table_name)

        # Common synonyms/aliases mapping
        synonyms = {
            "buyer": "customers",
            "purchaser": "customers",
            "client": "customers",
            "transaction": "orders",
            "purchase": "orders",
            "sale": "orders",
            "item": "order_items",
            "product": "products",
            "goods": "products",
            "category": "categories",
            "manager": "employees",
            "staff": "employees"
        }
        for syn, target_table in synonyms.items():
            if syn in question_lower and target_table in self.schema.tables:
                seed_tables.add(target_table)

        logger.debug(f"Identified seed tables for query '{question}': {seed_tables}")
        return seed_tables

    def get_relevant_schema_subset(self, question: str) -> DatabaseSchemaMetadata:
        """
        Extract only the relevant subset of the schema graph for the user question.
        Uses shortest path between all seed tables to ensure they can join,
        and adds directly adjacent tables if only one table is found.
        """
        seed_tables = self.identify_seed_tables(question)
        
        # If no tables were identified, return the full schema or a reasonable default subset
        if not seed_tables:
            logger.info("No seed tables identified. Returning full schema metadata.")
            return self.schema

        relevant_tables: Set[str] = set(seed_tables)
        
        # Find paths connecting all pairs of seed tables
        seed_list = list(seed_tables)
        for i in range(len(seed_list)):
            for j in range(i + 1, len(seed_list)):
                path = self.find_shortest_path(seed_list[i], seed_list[j])
                relevant_tables.update(path)

        # If only one table is relevant, include its 1-hop neighbors so it has context for basic joins
        if len(relevant_tables) == 1:
            only_table = next(iter(relevant_tables))
            relevant_tables.update(self.graph.get(only_table, []))

        # Build schema subset
        subset = DatabaseSchemaMetadata()
        for t in relevant_tables:
            if t in self.schema.tables:
                subset.tables[t] = self.schema.tables[t]

        logger.info(f"Retrieved schema subset containing {len(subset.tables)} tables (from {len(self.schema.tables)} total tables) for query: '{question}'")
        return subset

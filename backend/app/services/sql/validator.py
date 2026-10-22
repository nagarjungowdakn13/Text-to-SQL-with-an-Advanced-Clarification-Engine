from typing import List, Tuple, Set, Optional
import sqlglot
import sqlglot.expressions as exp
from app.services.schema.extractor import DatabaseSchemaMetadata
from app.core.logging import logger

class SQLValidationError(Exception):
    """Exception raised when a SQL query violates security or syntactic checks."""
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or [message]

class SQLValidator:
    DANGEROUS_FUNCTIONS = {
        "pg_sleep", "pg_read_file", "pg_write_file", "pg_ls_dir", 
        "pg_execute_server_program", "copy", "version", "current_setting"
    }

    @staticmethod
    def validate(sql: str, schema: DatabaseSchemaMetadata) -> Tuple[bool, List[str]]:
        """
        Validate SQL for syntax, table/column allowlist, DDL/DML protection,
        Cartesian joins, and dangerous functions.
        Returns (is_valid, list_of_errors).
        """
        errors = []
        if not sql or not sql.strip():
            return False, ["Query is empty."]

        # 1. Parse validation
        try:
            # We parse using postgres dialect
            parsed = sqlglot.parse_one(sql, read="postgres")
        except Exception as e:
            logger.warning(f"SQL Syntax parsing failed: {e}")
            return False, [f"SQL Syntax Error: {str(e)}"]

        # 2. Statement type validation (Enforce SELECT only)
        if not isinstance(parsed, exp.Select):
            errors.append("Invalid query type: Only SELECT queries are permitted.")
            return False, errors

        # 3. Check for modification operations inside subqueries or CTEs
        for expression in parsed.walk():
            # If we find any insert/update/delete/ddl expressions
            if isinstance(expression, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter)):
                errors.append("Forbidden statement type: Modifying database structure or rows is rejected.")
                break

        # 4. Check for dangerous function calls
        for function in parsed.find_all(exp.Anonymous):
            func_name = function.name.lower()
            if func_name in SQLValidator.DANGEROUS_FUNCTIONS:
                errors.append(f"Forbidden function call: '{func_name}' is dangerous and blocked.")

        for function in parsed.find_all(exp.Func):
            func_name = function.sql_name().lower()
            if func_name in SQLValidator.DANGEROUS_FUNCTIONS:
                errors.append(f"Forbidden function call: '{func_name}' is dangerous and blocked.")

        # 5. Extract tables and check allowlist
        allowed_tables = set(schema.tables.keys())
        queried_tables: List[exp.Table] = list(parsed.find_all(exp.Table))
        
        table_aliases = {}  # Map alias -> true table name
        
        # Resolve aliases in select projection/joins
        for t in queried_tables:
            t_name = t.name
            t_alias = t.alias
            
            # Check table allowlist
            if t_name and t_name not in allowed_tables:
                errors.append(f"Access denied: Table '{t_name}' does not exist in schema allowlist.")
            
            if t_alias:
                table_aliases[t_alias] = t_name
            else:
                table_aliases[t_name] = t_name

        # 6. Check columns allowlist
        # Retrieve all column names per table for lookups
        table_columns_map: Dict[str, Set[str]] = {}
        all_allowed_columns: Set[str] = set()
        for t_name, t_meta in schema.tables.items():
            table_columns_map[t_name] = {c.name for c in t_meta.columns}
            all_allowed_columns.update(table_columns_map[t_name])

        # Extract all projection aliases (e.g. SELECT COUNT(*) AS order_count)
        # These can be referenced in GROUP BY or ORDER BY clauses and are valid!
        projection_aliases = set()
        for select_node in parsed.find_all(exp.Select):
            for expr in select_node.expressions:
                if isinstance(expr, exp.Alias):
                    projection_aliases.add(expr.alias.lower())

        for col in parsed.find_all(exp.Column):
            col_name = col.name.lower()
            col_table = col.table  # prefix table or alias (e.g. 'c' in 'c.customer_id')

            # Skip validation if column is a valid projection alias in the query
            if col_name in projection_aliases:
                continue

            if col_table:
                # Find real table name from alias
                real_table = table_aliases.get(col_table)
                if not real_table:
                    # Maybe the user used the actual table name instead of alias prefix
                    real_table = col_table if col_table in allowed_tables else None
                
                if real_table:
                    allowed_cols = table_columns_map.get(real_table, set())
                    if col.name not in allowed_cols:
                        errors.append(f"Access denied: Column '{col.name}' does not exist on table '{real_table}'.")
                else:
                    errors.append(f"Access denied: Prefix '{col_table}' on column '{col.name}' could not be resolved.")
            else:
                # If no prefix, check if the column exists in ANY table in the schema
                if col.name not in all_allowed_columns:
                    errors.append(f"Access denied: Column '{col.name}' does not exist in the active schema tables.")

        # 7. Cartesian Join Detection (Cross Join checks)
        # Check explicit Joins
        for join in parsed.find_all(exp.Join):
            # In sqlglot, check if cross join or missing 'on' clause (excluding USING)
            join_args = join.args
            is_cross = join_args.get("method") == "CROSS" or join.method == "CROSS"
            has_on = join_args.get("on") is not None
            has_using = join_args.get("using") is not None
            
            # If join doesn't have an ON or USING condition, and is not a CROSS join
            # Note: Cross joins are dangerous, but sometimes explicitly written. We block them by default.
            if is_cross:
                errors.append("Unsafe query: Cartesian product (CROSS JOIN) detected and blocked.")
            elif not has_on and not has_using:
                # Natural join or missing condition
                errors.append("Unsafe query: JOIN without ON/USING condition (implicit Cartesian product) detected and blocked.")

        # Check implicit FROM list joins: e.g., SELECT * FROM table1, table2
        from_expr = parsed.args.get("from")
        joins_expr = parsed.args.get("joins")
        
        # If there are multiple items in the FROM clause, it's an implicit cross join
        if from_expr and hasattr(from_expr, "expressions") and len(from_expr.expressions) > 1:
            errors.append("Unsafe query: Comma-separated FROM tables (implicit Cartesian product) detected and blocked.")

        return len(errors) == 0, errors

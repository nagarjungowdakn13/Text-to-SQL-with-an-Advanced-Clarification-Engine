import time
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.logging import logger

class DatabaseExecutor:
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        
        # Configure engine options
        engine_args = {}
        connect_args = {}
        if connection_url.startswith("postgresql"):
            # Set a session statement timeout at connection time (in milliseconds)
            timeout_ms = settings.QUERY_TIMEOUT_SECONDS * 1000
            connect_args = {
                "options": f"-c statement_timeout={timeout_ms}"
            }
            engine_args = {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_recycle": 1800
            }
        elif connection_url.startswith("sqlite"):
            # Set timeout in seconds for SQLite lock contention
            connect_args = {
                "timeout": settings.QUERY_TIMEOUT_SECONDS,
                "check_same_thread": False
            }
            # Use StaticPool for in-memory SQLite to share data across connection threads
            if ":memory:" in connection_url:
                from sqlalchemy.pool import StaticPool
                engine_args = {
                    "poolclass": StaticPool
                }

        self.engine = create_engine(
            connection_url,
            connect_args=connect_args,
            **engine_args
        )
        logger.info(f"DatabaseExecutor initialized for execution DB.")

    def execute_query(self, sql: str) -> Tuple[List[str], List[Dict[str, Any]], float, Optional[str]]:
        """
        Execute SQL query against target database.
        Returns (columns, rows, execution_time_ms, error_message).
        """
        columns: List[str] = []
        rows: List[Dict[str, Any]] = []
        execution_time_ms = 0.0
        error_message = None

        start_time = time.perf_counter()
        
        try:
            with self.engine.connect() as conn:
                # Execute query
                result = conn.execute(text(sql))
                
                # Fetch columns
                if result.returns_rows:
                    columns = list(result.keys())
                    
                    # Fetch rows up to max limits
                    row_count = 0
                    for row in result:
                        row_count += 1
                        if row_count > settings.MAX_EXECUTION_ROWS:
                            logger.warning(f"Result set capped at max execution rows: {settings.MAX_EXECUTION_ROWS}")
                            break
                            
                        # Build serializable dictionary
                        row_dict = {}
                        for idx, col_name in enumerate(columns):
                            val = row[idx]
                            # Serialize binary/datetime objects to strings
                            if isinstance(val, bytes):
                                val = val.hex()
                            elif val is not None and not isinstance(val, (int, float, str, bool)):
                                val = str(val)
                            row_dict[col_name] = val
                        rows.append(row_dict)

            execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Query executed successfully in {execution_time_ms:.2f}ms. Returned {len(rows)} rows.")
            
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            error_message = str(e)
            logger.error(f"Database execution error in {execution_time_ms:.2f}ms: {error_message}")

        return columns, rows, execution_time_ms, error_message

    def explain_query(self, sql: str) -> Tuple[str, Optional[str]]:
        """
        Run EXPLAIN on the SQL query to inspect query plan.
        """
        try:
            # Prefix with EXPLAIN or EXPLAIN ANALYZE (safe read-only check)
            # In SQLite, it is EXPLAIN QUERY PLAN
            explain_keyword = "EXPLAIN"
            if self.connection_url.startswith("sqlite"):
                explain_keyword = "EXPLAIN QUERY PLAN"

            explain_sql = f"{explain_keyword} {sql}"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(explain_sql))
                plan_lines = []
                for row in result:
                    plan_lines.append(str(row[0]))
                return "\n".join(plan_lines), None
        except Exception as e:
            logger.error(f"Failed to explain query: {e}")
            return "", str(e)

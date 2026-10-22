from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy import inspect, create_engine, text
from app.core.config import settings
from app.core.logging import logger

class ColumnMetadata(BaseModel):
    name: str
    data_type: str
    is_nullable: bool
    default: Optional[str] = None
    comment: Optional[str] = None
    sample_values: List[Any] = Field(default_factory=list)

class ForeignKeyMetadata(BaseModel):
    constrained_columns: List[str]
    referred_table: str
    referred_columns: List[str]

class TableMetadata(BaseModel):
    name: str
    comment: Optional[str] = None
    columns: List[ColumnMetadata] = Field(default_factory=list)
    primary_keys: List[str] = Field(default_factory=list)
    foreign_keys: List[ForeignKeyMetadata] = Field(default_factory=list)
    row_count: int = 0

class DatabaseSchemaMetadata(BaseModel):
    tables: Dict[str, TableMetadata] = Field(default_factory=dict)

class SchemaExtractor:
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        connect_args = {}
        if connection_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        self.engine = create_engine(connection_url, connect_args=connect_args)
        logger.info(f"SchemaExtractor initialized for: {connection_url.split('@')[-1] if '@' in connection_url else connection_url}")

    def extract_schema(self) -> DatabaseSchemaMetadata:
        """Extract the full metadata from the connected database."""
        schema_metadata = DatabaseSchemaMetadata()
        try:
            inspector = inspect(self.engine)
            table_names = inspector.get_table_names()
            
            with self.engine.connect() as conn:
                for table in table_names:
                    logger.debug(f"Extracting schema for table: {table}")
                    
                    # 1. Row count
                    row_count = 0
                    try:
                        row_count_res = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        row_count = row_count_res.scalar() or 0
                    except Exception as e:
                        logger.warning(f"Failed to get row count for table {table}: {e}")
                    
                    # 2. Sample records
                    sample_rows = []
                    try:
                        sample_res = conn.execute(text(f"SELECT * FROM {table} LIMIT 3"))
                        columns_list = sample_res.keys()
                        for row in sample_res:
                            # Convert row values to string/serializable values
                            row_dict = {}
                            for col_idx, col_name in enumerate(columns_list):
                                val = row[col_idx]
                                # Convert bytes or complex types to strings
                                if isinstance(val, bytes):
                                    val = val.hex()
                                elif val is not None and not isinstance(val, (int, float, str, bool)):
                                    val = str(val)
                                row_dict[col_name] = val
                            sample_rows.append(row_dict)
                    except Exception as e:
                        logger.warning(f"Failed to get sample rows for table {table}: {e}")

                    # 3. Columns
                    columns_meta = []
                    columns = inspector.get_columns(table)
                    pks = inspector.get_pk_constraint(table).get("constrained_columns", [])
                    
                    for col in columns:
                        col_name = col["name"]
                        
                        # Get sample values for this specific column
                        col_samples = []
                        for sample in sample_rows:
                            if col_name in sample and sample[col_name] is not None:
                                col_samples.append(sample[col_name])
                                
                        col_meta = ColumnMetadata(
                            name=col_name,
                            data_type=str(col["type"]),
                            is_nullable=col["nullable"],
                            default=str(col["default"]) if col.get("default") is not None else None,
                            comment=col.get("comment"),
                            sample_values=col_samples[:3]
                        )
                        columns_meta.append(col_meta)
                    
                    # 4. Foreign Keys
                    fkeys_meta = []
                    fkeys = inspector.get_foreign_keys(table)
                    for fk in fkeys:
                        fk_meta = ForeignKeyMetadata(
                            constrained_columns=fk["constrained_columns"],
                            referred_table=fk["referred_table"],
                            referred_columns=fk["referred_columns"]
                        )
                        fkeys_meta.append(fk_meta)

                    # 5. Table Comment
                    table_comment = None
                    try:
                        table_comment = inspector.get_table_comment(table).get("text")
                    except Exception:
                        pass

                    table_meta = TableMetadata(
                        name=table,
                        comment=table_comment,
                        columns=columns_meta,
                        primary_keys=pks,
                        foreign_keys=fkeys_meta,
                        row_count=row_count
                    )
                    schema_metadata.tables[table] = table_meta

            logger.info(f"Successfully extracted schema for {len(table_names)} tables.")
            return schema_metadata
        except Exception as e:
            logger.error(f"Error extracting schema from database: {e}")
            raise e

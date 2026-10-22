import json
from typing import Optional
import redis
from app.services.schema.extractor import DatabaseSchemaMetadata, SchemaExtractor
from app.core.config import settings
from app.core.logging import logger

class SchemaCache:
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.extractor = SchemaExtractor(connection_url)
        self._local_cache: Optional[DatabaseSchemaMetadata] = None
        self._redis_client: Optional[redis.Redis] = None
        
        if settings.REDIS_URL:
            try:
                self._redis_client = redis.from_url(settings.REDIS_URL)
                # Test connection
                self._redis_client.ping()
                logger.info("SchemaCache connected to Redis successfully.")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for caching: {e}. Falling back to in-memory cache.")
                self._redis_client = None

    def _get_redis_key(self) -> str:
        # Generate a unique key per connection string database name
        db_identifier = self.connection_url.split("/")[-1].split("?")[0]
        return f"querypilot:schema:{db_identifier}"

    def get_schema(self, force_refresh: bool = False) -> DatabaseSchemaMetadata:
        """Retrieve schema from cache, or extract it if not cached or force_refresh is True."""
        if force_refresh:
            logger.info("Forced schema refresh requested.")
            return self.refresh_schema()

        # Try In-memory local cache first
        if self._local_cache:
            logger.debug("Schema retrieved from in-memory cache.")
            return self._local_cache

        # Try Redis cache second
        if self._redis_client:
            try:
                cached_data = self._redis_client.get(self._get_redis_key())
                if cached_data:
                    logger.info("Schema retrieved from Redis cache.")
                    schema = DatabaseSchemaMetadata.model_validate_json(cached_data)
                    self._local_cache = schema
                    return schema
            except Exception as e:
                logger.warning(f"Error fetching schema from Redis: {e}")

        # If cache miss, extract it
        logger.info("Schema cache miss. Extracting schema directly from database.")
        schema = self.extractor.extract_schema()
        self.set_schema(schema)
        return schema

    def set_schema(self, schema: DatabaseSchemaMetadata):
        """Set the schema in the cache."""
        self._local_cache = schema
        
        if self._redis_client:
            try:
                redis_key = self._get_redis_key()
                # Cache for 24 hours
                self._redis_client.setex(
                    redis_key,
                    86400,
                    schema.model_dump_json()
                )
                logger.info(f"Schema cached in Redis with key: {redis_key}")
            except Exception as e:
                logger.warning(f"Failed to write schema to Redis cache: {e}")

    def refresh_schema(self) -> DatabaseSchemaMetadata:
        """Extract latest database schema and update caches."""
        schema = self.extractor.extract_schema()
        self.set_schema(schema)
        return schema

    def clear_cache(self):
        """Clear cache state."""
        self._local_cache = None
        if self._redis_client:
            try:
                self._redis_client.delete(self._get_redis_key())
                logger.info("Redis schema cache cleared.")
            except Exception as e:
                logger.warning(f"Failed to clear Redis schema cache: {e}")

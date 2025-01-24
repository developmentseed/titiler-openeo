"""titiler.openeo.services Parquet."""

import uuid
from typing import Any, Dict

import duckdb
from attrs import define

from .duckdb_base import DuckDBBaseStore


@define()
class ParquetStore(DuckDBBaseStore):
    """DuckDB Service Store using Parquet format."""

    def _get_connection(self):
        """Get database connection."""
        return duckdb.connect(database=":memory:")

    def _get_table_query(self) -> str:
        """Get query to access services table."""
        return f"read_parquet('{self.store}')"

    def add_service(self, user_id: str, service: Dict, **kwargs) -> str:
        """Add Service."""
        service_id = str(uuid.uuid4())
        with self._get_connection() as con:
            try:
                con.execute(
                    f"""
                    CREATE TABLE services AS 
                    SELECT * FROM {self._get_table_query()}
                    """
                )
            except:
                # File doesn't exist or is empty, create new table
                con.execute(
                    """
                    CREATE TABLE services (
                        service_id VARCHAR,
                        user_id VARCHAR,
                        service JSON
                    )
                    """
                )

            # Insert new service
            con.execute(
                """
                INSERT INTO services VALUES (?, ?, ?)
                """,
                [service_id, user_id, service],
            )

            # Write back to parquet
            con.execute(
                """
                COPY services TO ? (FORMAT PARQUET, OVERWRITE TRUE)
                """,
                [self.store],
            )

        return service_id

    def delete_service(self, service_id: str, **kwargs) -> bool:
        """Delete Service."""
        with self._get_connection() as con:
            # Load existing data
            con.execute(
                f"""
                CREATE TABLE services AS 
                SELECT * FROM {self._get_table_query()}
                """
            )

            # Delete service
            result = con.execute(
                """
                DELETE FROM services
                WHERE service_id = ?
                RETURNING service_id
                """,
                [service_id],
            ).fetchone()

            if not result:
                raise ValueError(f"Could not find service: {service_id}")

            # Write back to parquet
            con.execute(
                """
                COPY services TO ? (FORMAT PARQUET, OVERWRITE TRUE)
                """,
                [self.store],
            )

        return True

    def update_service(self, user_id: str, item_id: str, val: Dict[str, Any], **kwargs) -> str:
        """Update Service."""
        with self._get_connection() as con:
            # Load all data
            con.execute(
                f"""
                CREATE TABLE services AS 
                SELECT * FROM {self._get_table_query()}
                """
            )

            # Verify service exists and belongs to user
            result = con.execute(
                """
                SELECT user_id, service
                FROM services
                WHERE service_id = ?
                """,
                [item_id],
            ).fetchone()

            if not result:
                raise ValueError(f"Could not find service: {item_id}")

            if result[0] != user_id:
                raise ValueError(f"Service {item_id} does not belong to user {user_id}")

            # Merge the existing service with updates
            service = result[1]
            service.update(val)

            # Update service
            con.execute(
                """
                UPDATE services
                SET service = ?
                WHERE service_id = ?
                """,
                [service, item_id],
            )

            # Write back to parquet
            con.execute(
                """
                COPY services TO ? (FORMAT PARQUET, OVERWRITE TRUE)
                """,
                [self.store],
            )

        return item_id
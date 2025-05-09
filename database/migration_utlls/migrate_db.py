from sqlalchemy import create_engine, text, MetaData, Table, select
from sqlalchemy.engine import Engine
from typing import Optional
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self, source_db_url: str, target_db_url: str):
        """
        Initialize the DatabaseMigrator with source and target database URLs.
        
        Args:
            source_db_url (str): SQLAlchemy URL for source database
            target_db_url (str): SQLAlchemy URL for target database
        """
        self.source_db_url = source_db_url
        self.target_db_url = target_db_url
        self.source_engine: Optional[Engine] = None
        self.target_engine: Optional[Engine] = None

    def connect(self):
        """Establish connections to both source and target databases."""
        try:
            self.source_engine = create_engine(self.source_db_url)
            self.target_engine = create_engine(self.target_db_url)
            logger.info("Successfully connected to both source and target databases")
        except Exception as e:
            logger.error(f"Failed to connect to databases: {str(e)}")
            raise

    def disconnect(self):
        """Close connections to both databases."""
        if self.source_engine:
            self.source_engine.dispose()
        if self.target_engine:
            self.target_engine.dispose()
        logger.info("Database connections closed")

    @contextmanager
    def get_connections(self):
        """Context manager for database connections."""
        if not self.source_engine or not self.target_engine:
            self.connect()
        
        source_conn = self.source_engine.connect()
        target_conn = self.target_engine.connect()
        try:
            yield source_conn, target_conn
        finally:
            source_conn.close()
            target_conn.close()

    def migrate_table(self, table_name: str, batch_size: int = 1000) -> bool:
        """
        Migrate data from source table to target table.
        
        Args:
            table_name (str): Name of the table to migrate
            batch_size (int): Number of records to process in each batch
            
        Returns:
            bool: True if migration was successful, False otherwise
        """
        try:
            with self.get_connections() as (source_conn, target_conn):
                # Get table metadata
                metadata = MetaData()
                source_table = Table(table_name, metadata, autoload_with=self.source_engine)
                
                # Get total count of records
                count_query = select(text('COUNT(*)')).select_from(source_table)
                total_records = source_conn.execute(count_query).scalar()
                logger.info(f"Total records to migrate: {total_records}")

                # Process records in batches
                offset = 0
                while True:
                    # Fetch batch of records
                    query = select(source_table).limit(batch_size).offset(offset)
                    result = source_conn.execute(query)
                    
                    # Convert to list of dictionaries properly
                    batch_data = []
                    for row in result:
                        row_dict = {}
                        for column in source_table.columns:
                            row_dict[column.name] = getattr(row, column.name)
                        batch_data.append(row_dict)
                    
                    if not batch_data:
                        break

                    # Insert batch into target database
                    target_conn.execute(
                        source_table.insert(),
                        batch_data
                    )
                    target_conn.commit()

                    offset += batch_size
                    logger.info(f"Migrated {min(offset, total_records)} of {total_records} records")

                logger.info(f"Successfully migrated table: {table_name}")
                return True

        except Exception as e:
            logger.error(f"Error during table migration: {str(e)}")
            if 'target_conn' in locals():
                target_conn.rollback()
            return False

# Example usage:
if __name__ == "__main__":
    # Example database URLs
    source_db_url = "postgresql://postgres@localhost:5432/chat_db"
    target_db_url = "postgresql://postgres@localhost:5432/mayday"
    
    # Create migrator instance
    migrator = DatabaseMigrator(source_db_url, target_db_url)
    
    try:
        # Migrate a specific table
        success = migrator.migrate_table("documents")
        if success:
            print("Migration completed successfully")
        else:
            print("Migration failed")
    finally:
        migrator.disconnect()

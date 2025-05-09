from database.db import engine
from database.models import Base
from sqlalchemy import inspect

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

def create_specific_table(table_name: str):
    """
    Create a specific table based on the models defined in Base.
    
    Args:
        table_name (str): Name of the table to create
        
    Returns:
        bool: True if table was created successfully, False if table doesn't exist in models
    """
    # Get all tables from the Base metadata
    tables = Base.metadata.tables
    
    # Check if the requested table exists in our models
    if table_name not in tables:
        print(f"Error: Table '{table_name}' not found in models")
        return False
    
    # Create only the specified table
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        tables[table_name].create(bind=engine)
        print(f"Table '{table_name}' created successfully!")
    else:
        print(f"Table '{table_name}' already exists")
    return True

if __name__ == "__main__":
    # init_db()
    create_specific_table("company_resources")
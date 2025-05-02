from sqlalchemy import text
from database.db import engine, Base

def recreate_tables():
    # Drop all tables
    Base.metadata_fields.drop_all(bind=engine)
    print("All tables dropped successfully!")
    
    # Recreate all tables
    Base.metadata_fields.create_all(bind=engine)
    print("Database tables recreated successfully!")

if __name__ == "__main__":
    recreate_tables() 
#!/usr/bin/env python
import json
import os
import sys

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.db import SessionLocal
from database.models import CompanyConfig

def populate_config():
    # Open database session
    db = SessionLocal()
    
    try:
        # Read config from JSON file
        with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r') as f:
            config_data = json.load(f)
        
        # Count for reporting
        inserted_count = 0
        skipped_count = 0
        
        # Process each config entry
        for config_entry in config_data:
            # Check if config already exists (by company_id)
            existing_config = db.query(CompanyConfig).filter(
                CompanyConfig.company_id == config_entry['company_id']
            ).first()
            
            if existing_config:
                print(f"Config for company {config_entry['company_id']} already exists. Skipping.")
                skipped_count += 1
                continue
            
            # Create new config
            new_config = CompanyConfig(
                company_id=config_entry['company_id'],
                storage_location=config_entry['storage_location']
            )
            
            # Add to session
            db.add(new_config)
            inserted_count += 1
        
        # Commit all changes
        db.commit()
        print(f"Config import completed: {inserted_count} inserted, {skipped_count} skipped.")
    
    except Exception as e:
        db.rollback()
        print(f"Error inserting config: {str(e)}")
    
    finally:
        # Close the session
        db.close()

# this works.
if __name__ == "__main__":
    populate_config()

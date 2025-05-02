#!/usr/bin/env python
import json
import os
import sys

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import SessionLocal
from database.models import Company

def insert_companies():
    # Open database session
    db = SessionLocal()
    
    try:
        # Read companies from JSON file
        with open(os.path.join(os.path.dirname(__file__), 'companies.json'), 'r') as f:
            companies_data = json.load(f)
        
        # Count for reporting
        inserted_count = 0
        skipped_count = 0
        
        # Process each company
        for company_data in companies_data:
            # Check if company already exists (by ticker)
            existing_company = db.query(Company).filter(Company.ticker == company_data['ticker']).first()
            
            if existing_company:
                print(f"Company with ticker {company_data['ticker']} already exists. Skipping.")
                skipped_count += 1
                continue
            
            # Create new company
            new_company = Company(
                ticker=company_data['ticker'],
                name=company_data['name']
            )
            
            # Add to session
            db.add(new_company)
            inserted_count += 1
        
        # Commit all changes
        db.commit()
        print(f"Companies import completed: {inserted_count} inserted, {skipped_count} skipped.")
    
    except Exception as e:
        db.rollback()
        print(f"Error inserting companies: {str(e)}")
    
    finally:
        # Close the session
        db.close()

if __name__ == "__main__":
    insert_companies()

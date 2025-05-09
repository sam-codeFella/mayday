#!/usr/bin/env python3
import os
import sys
import logging
from sqlalchemy import text, select, update
from dotenv import load_dotenv

from database.db import get_db
from database.models import Document, CompanyResource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def transform_path(file_path):
    """
    Transform path from old format to new format for comparison
    """
    if file_path and '/aha/new_backend/' in file_path:
        return file_path.replace('/aha/new_backend/', '/shams/mayday/')
    return file_path

def map_documents_to_resources():
    """
    Maps documents to their corresponding resources based on file path.
    
    1. Gets all distinct file paths from documents table
    2. For each path, finds matching company_resource based on source_location
    3. Updates all documents with that path to use the found resource_id
    """
    load_dotenv()
    
    # Use the existing database session
    db = next(get_db())
    
    try:
        # Get all distinct file paths from documents table
        distinct_paths_query = select(Document.file_path).distinct().where(
            Document.resource_id.is_(None),
            Document.file_path.is_not(None)
        )
        distinct_paths = [path[0] for path in db.execute(distinct_paths_query).all()]
        
        logger.info(f"Found {len(distinct_paths)} distinct file paths to process")
        
        paths_mapped = 0
        paths_not_found = 0
        
        # Process each distinct path
        for file_path in distinct_paths:
            # Transform the path for comparison
            transformed_path = transform_path(file_path)
            
            # Look for matching company resource
            resource_query = select(CompanyResource).where(
                CompanyResource.source_location == transformed_path
            )
            resource = db.execute(resource_query).scalar_one_or_none()
            
            if resource:
                # Update all documents with this path
                update_query = (
                    update(Document)
                    .where(Document.file_path == file_path)
                    .values(resource_id=resource.id)
                )
                result = db.execute(update_query)
                db.commit()
                
                logger.info(f"Updated {result.rowcount} documents with resource_id {resource.id} for path: {file_path}")
                paths_mapped += 1
            else:
                logger.warning(f"No matching resource found for path: {file_path} (transformed: {transformed_path})")
                paths_not_found += 1
        
        logger.info(f"Mapping complete: {paths_mapped} paths mapped, {paths_not_found} paths not found")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during document-resource mapping: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting document to resource mapping process")
    map_documents_to_resources()
    logger.info("Document to resource mapping process completed")

# new path - /Users/shams/Desktop/Panache/Cursor/shams/mayday/utils/documents/yatharth/2024/investor_meet_intimiation.pdf
# old path - /Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2024/investor_meet_intimiation.pdf
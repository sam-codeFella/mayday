import os
import boto3
import json
import uuid
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dotenv import load_dotenv
load_dotenv() # to load all the env variables exposed from .env file.
from sqlalchemy import text
from sqlalchemy.orm import Session

# Import the get_db function from the database module
from database.db import get_db
from database.models import CompanyConfig, CompanyResource

load_dotenv() # to load all the env variables exposed from .env file.

class S3Uploader:
    def __init__(self, company_id: str, storage_location: str = None, region: str = "ap-south-1"):
        """
        Initialize S3Uploader with company configuration
        
        Args:
            company_id (str): Company identifier
            storage_location (str, optional): Storage location string from DB in format 'bucket-name/folder/path'.
                                              If None, it will be fetched from the database.
            region (str): AWS region for the S3 bucket, defaults to ap-south-1
        """
        self.company_id = company_id
        self.region = region
        
        # If storage_location not provided, fetch it from the database
        if not storage_location:
            storage_location = self._get_storage_location_from_db()
            
        self.bucket_name, self.folder_prefix = self._parse_storage_location(storage_location)
        self.s3_client = boto3.client('s3', region_name=self.region)

    def _get_storage_location_from_db(self) -> str:
        """
        Query the database to get the storage location for the company using the existing get_db function
        
        Returns:
            str: Storage location string
        """
        try:
            # Get database session using the existing get_db function which is a generator
            # Use next() to get the actual session
            db = next(get_db())
            
            try:
                # Query for company configuration using the ORM approach
                company_config = db.query(CompanyConfig).filter(
                    CompanyConfig.company_id == self.company_id
                ).first()
                
                if not company_config:
                    # Fallback to raw SQL if ORM query fails
                    result = db.execute(
                        text("SELECT storage_location FROM company_config WHERE company_id = :company_id"),
                        {"company_id": self.company_id}
                    ).first()
                    
                    if not result:
                        raise ValueError(f"No company configuration found for company_id: {self.company_id}")
                    
                    storage_location = result[0]
                else:
                    storage_location = company_config.storage_location
                
                if not storage_location:
                    raise ValueError(f"No storage location found for company_id: {self.company_id}")
                
                return storage_location
            
            finally:
                # Close the session if needed
                if hasattr(db, 'close'):
                    db.close()
            
        except Exception as e:
            raise Exception(f"Error fetching storage location from database: {str(e)}")

    def _format_s3_url(self, bucket: str, key: str) -> str:
        """
        Format the S3 URL in the required format
        
        Args:
            bucket (str): Bucket name
            key (str): Object key
            
        Returns:
            str: Formatted URL
        """
        # URL encode the key for proper handling of spaces and special characters
        encoded_key = urllib.parse.quote(key)
        
        # Format as https://bucket-name.s3.region.amazonaws.com/key
        return f"https://{bucket}.s3.{self.region}.amazonaws.com/{encoded_key}"

    def _record_in_company_resource(self, file_path: str, s3_url: str) -> bool:
        """
        Record the uploaded file in the CompanyResource table
        
        Args:
            file_path (str): Local file path
            s3_url (str): S3 URL in the format https://bucket.s3.region.amazonaws.com/key
            
        Returns:
            bool: True if recording was successful, False otherwise
        """
        try:
            # Get database session - get_db() is a generator, so use next()
            db = next(get_db())
            
            try:
                # Get absolute path of the file
                abs_file_path = os.path.abspath(file_path)
                
                # Create a new CompanyResource record using the correct schema
                new_resource = CompanyResource(
                    id=uuid.uuid4(),  # UUID field as primary key
                    company_id=uuid.UUID(self.company_id),  # Convert string to UUID
                    resource_location=s3_url,  # S3 URL path for the resource
                    source_location=abs_file_path,  # Absolute local file path
                    is_ingested=False,  # Default is False as per schema
                    created_at=datetime.utcnow()  # Current UTC time
                )
                
                # Add and commit to database
                db.add(new_resource)
                db.commit()
                
                return True
                
            except Exception as e:
                db.rollback()
                print(f"Error recording resource in database: {str(e)}")
                return False
                
            finally:
                # Close the session if needed
                if hasattr(db, 'close'):
                    db.close()
                    
        except Exception as e:
            print(f"Database connection error: {str(e)}")
            return False

    def _get_file_type(self, filename: str) -> str:
        """
        Determine file type based on file extension
        
        Args:
            filename (str): Name of the file
            
        Returns:
            str: File type (extension without the dot)
        """
        _, ext = os.path.splitext(filename)
        if ext:
            # Remove the dot and return lowercase extension
            return ext[1:].lower()
        return "unknown"

    def _parse_storage_location(self, storage_location: str) -> Tuple[str, str]:
        """
        Parse storage location string to get bucket name and folder prefix
        
        Args:
            storage_location (str): Storage location string from DB (e.g. 'test-mayday/hospital/yatharth')
            
        Returns:
            Tuple[str, str]: Tuple containing (bucket_name, folder_prefix)
        """
        try:
            # Split on first occurrence of '/'
            parts = storage_location.split('/', 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid storage location format: {storage_location}")
            
            bucket_name = parts[0]
            folder_prefix = parts[1]
            
            return bucket_name, folder_prefix
        except Exception as e:
            raise Exception(f"Error parsing storage location: {str(e)}")

    def _get_all_files(self, directory: str) -> List[str]:
        """
        Recursively get all files from a directory
        
        Args:
            directory (str): Path to the directory to scan
            
        Returns:
            List[str]: List of absolute file paths
        """
        all_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                all_files.append(os.path.join(root, file))
        return all_files

    def upload_files(self, local_path: str) -> Dict[str, Any]:
        """
        Upload files from local directory to S3 based on company configuration
        
        Args:
            local_path (str): Local directory path containing files to upload
            
        Returns:
            Dict[str, Any]: Upload status report
        """
        try:
            # Get all files from the directory
            files = self._get_all_files(local_path)
            if not files:
                return {"status": "error", "message": "No files found in the specified directory"}
            
            uploaded_files = []
            failed_files = []
            db_recorded_files = []
            db_failed_files = []

            # Upload each file
            for file_path in files:
                try:
                    # Calculate relative path to maintain directory structure
                    relative_path = os.path.relpath(file_path, local_path)
                    s3_key = f"{self.folder_prefix}/{relative_path}"
                    
                    # Format S3 URL in the required format
                    s3_url = self._format_s3_url(self.bucket_name, s3_key)

                    # Upload file
                    self.s3_client.upload_file(
                        Filename=file_path,
                        Bucket=self.bucket_name,
                        Key=s3_key
                    )
                    
                    # Record upload details
                    upload_info = {
                        "local_path": file_path,
                        "abs_path": os.path.abspath(file_path),
                        "s3_url": s3_url
                    }
                    uploaded_files.append(upload_info)
                    
                    # Record in CompanyResource table
                    if self._record_in_company_resource(file_path, s3_url):
                        db_recorded_files.append(upload_info)
                    else:
                        db_failed_files.append({
                            "file": file_path,
                            "abs_path": os.path.abspath(file_path),
                            "s3_url": s3_url,
                            "error": "Failed to record in database"
                        })
                        
                except Exception as e:
                    failed_files.append({
                        "file": file_path,
                        "error": str(e)
                    })

            return {
                "status": "success" if not failed_files and not db_failed_files else "partial_success",
                "uploaded_files": uploaded_files,
                "failed_files": failed_files,
                "db_recorded_files": db_recorded_files,
                "db_failed_files": db_failed_files,
                "total_files": len(files),
                "successful_uploads": len(uploaded_files),
                "failed_uploads": len(failed_files),
                "successful_db_records": len(db_recorded_files),
                "failed_db_records": len(db_failed_files)
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


def main():
    """
    Example usage of the S3Uploader class
    """
    try:
        # Company ID to use for fetching configuration
        company_id = "0fbe6ad2-39c2-4d61-a731-9a538d907ab5"
        
        # Initialize uploader with company ID only
        # It will automatically fetch the storage location from the database
        uploader = S3Uploader(company_id=company_id, region="ap-south-1")

        # Define local directory to upload
        local_directory = "/Users/shams/Desktop/Panache/Cursor/shams/mayday/utils/documents/yatharth"

        # Upload files and get result
        result = uploader.upload_files(local_directory)

        # Print upload results
        if result["status"] == "success":
            print("All files uploaded successfully and recorded in database!")
            print(f"Total files uploaded: {result['successful_uploads']}")
        elif result["status"] == "partial_success":
            print("Some files were uploaded with issues:")
            print(f"Successfully uploaded: {result['successful_uploads']} files")
            print(f"Failed uploads: {result['failed_uploads']} files")
            print(f"Recorded in database: {result['successful_db_records']} files")
            print(f"Failed to record in database: {result['failed_db_records']} files")
            
            if result["failed_files"]:
                print("\nFailed uploads:")
                for failed in result["failed_files"]:
                    print(f"- {failed['file']}: {failed['error']}")
                    
            if result["db_failed_files"]:
                print("\nFailed database records:")
                for failed in result["db_failed_files"]:
                    print(f"- {failed['file']} (uploaded to {failed['s3_url']}): {failed['error']}")
        else:
            print(f"Error: {result['message']}")

        # Print detailed successful uploads if needed
        print("\nSuccessfully uploaded and recorded files:")
        for upload in result.get("db_recorded_files", []):
            print(f"Local: {upload['abs_path']}")
            print(f"S3: {upload['s3_url']}")
            print("---")

    except Exception as e:
        print(f"Error initializing uploader: {str(e)}")


if __name__ == "__main__":
    main()

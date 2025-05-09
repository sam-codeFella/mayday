import os
import uuid
import io
import tempfile
import boto3
from typing import List
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader, PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter

# Import database modules
from database.db import get_db, SessionLocal
from database.models import Document, Chunk, Company, CompanyResource

load_dotenv()


# Step 1 of ingestion - process PDF content directly from bytes
def extract_pdf_content_to_document_db(pdf_content: bytes, s3_url: str, company_id: str, resource_id: str, chunk_size: int = 1000, chunk_overlap: int = 50):
    """
    Extract content from PDF bytes and store each page as a separate document.
    Then, create chunks from these documents and store them in the chunks database.

    Args:
        pdf_content: Binary content of the PDF file
        s3_url: The S3 URL of the PDF (for reference)
        company_id: ID of the company
        resource_id: ID of the resource in company_resources table
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
    """
    print(f"Processing PDF from S3: {s3_url}")
    
    # Check if the content is actually a PDF
    if not pdf_content.startswith(b'%PDF-'):
        print(f"Warning: Content does not appear to be a PDF. First bytes: {pdf_content[:20]}")
        if pdf_content.startswith(b'\x00\x00\x00\x01Bud1') or pdf_content.startswith(b'Bud1'):
            print("This appears to be a macOS system file, not a PDF")
            return

    # Create a temporary file to store the PDF content
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        try:
            # Write PDF content to temporary file
            temp_file.write(pdf_content)
            temp_file.flush()
            
            # Load the PDF using the temporary file path
            loader = PyPDFLoader(temp_file.name)
            pages = loader.load()
            
            print(f"Found {len(pages)} pages in the PDF")
            
            # Save to document database
            db = SessionLocal()
            try:
                # Save each page as a separate document
                for i, page in enumerate(pages):
                    # Create document record for this page
                    document = Document(
                        id=uuid.uuid4(),
                        company_id=company_id,
                        resource_id=resource_id,
                        text=page.page_content,
                        page_number=i + 1,
                        file_path=s3_url  # Store S3 URL instead of local path
                    )
                    db.add(document)
                    db.commit()
                    db.refresh(document)

                    print(f"Document saved for page {i + 1} with ID: {document.id}")

                    # Create chunks from the document
                    text_splitter = CharacterTextSplitter(
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        separator="\n"
                    )

                    # Split the text into chunks
                    text_chunks = text_splitter.split_text(page.page_content)

                    for chunk_text in text_chunks:
                        chunk = Chunk(
                            id=uuid.uuid4(),
                            document_id=document.id,
                            company_id=company_id,
                            text=chunk_text
                        )
                        db.add(chunk)

                    db.commit()
                    print(f"Created and saved {len(text_chunks)} chunks from document {document.id} (page {i + 1})")
            finally:
                db.close()
        finally:
            # Clean up the temporary file
            os.unlink(temp_file.name)


def process_documents_to_chunks():
    """
    Read all documents from the database and create chunks for any that don't have chunks yet.
    """
    db = SessionLocal()
    try:
        # Get all documents
        documents = db.query(Document).all()
        print(f"Found {len(documents)} documents in database")

        # For each document, check if it has chunks
        for document in documents:
            existing_chunks = db.query(Chunk).filter(Chunk.document_id == document.id).count()

            if existing_chunks == 0:
                print(f"Creating chunks for document {document.id}")

                # Check if document has page_number and file_path attributes
                if not hasattr(document, 'page_number') or document.page_number is None:
                    print(f"Document {document.id} missing page_number, setting default")
                    document.page_number = 0

                if not hasattr(document, 'file_path') or document.file_path is None:
                    print(f"Document {document.id} missing file_path, setting default")
                    document.file_path = "unknown_path"

                db.commit()

                # Create chunks for this document
                text_splitter = CharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=30,
                    separator="\n"
                )

                # Split the text into chunks
                text_chunks = text_splitter.split_text(document.text)

                for chunk_text in text_chunks:
                    chunk = Chunk(
                        id=uuid.uuid4(),
                        document_id=document.id,
                        company_id=document.company_id,
                        text=chunk_text
                    )
                    db.add(chunk)

                db.commit()
                print(f"Created {len(text_chunks)} chunks for document {document.id}")
            else:
                print(f"Document {document.id} already has {existing_chunks} chunks, skipping")

    finally:
        db.close()


def get_s3_file_content(s3_url: str):
    """
    Get the content of a file from S3 directly into memory
    
    Args:
        s3_url: URL of the file in S3 (https://bucket.s3.region.amazonaws.com/key)
        
    Returns:
        bytes: The content of the file if it's a valid PDF, None otherwise
    """
    try:
        # Parse the S3 URL to get bucket and key
        # Format is: https://bucket-name.s3.region.amazonaws.com/key
        parts = s3_url.replace('https://', '').split('/')
        s3_domain = parts[0]
        bucket_name = s3_domain.split('.')[0]
        key = '/'.join(parts[1:])
        
        print(f"Parsed S3 URL: bucket={bucket_name}, key={key}")
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Get the file content directly to memory
        print(f"Fetching from S3: {s3_url}")
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        
        # Check content type if available
        content_type = response.get('ContentType', '')
        print(f"Content type from S3: {content_type}")
        
        file_content = response['Body'].read()
        print(f"Successfully fetched file content from S3, size: {len(file_content)} bytes")
        
        # Check if the content has PDF signature
        if not file_content.startswith(b'%PDF-'):
            print(f"Warning: File doesn't appear to be a PDF (first 20 bytes: {file_content[:20]})")
            
            # If it's definitely not a PDF, return None
            if (
                file_content.startswith(b'Bud1') or  # macOS .DS_Store file
                file_content.startswith(b'\x00\x00\x00\x01Bud1')  # Another common binary format
            ):
                print("This appears to be a macOS system file or other binary data, not a PDF")
                return None
            
            # If unsure, we'll still attempt to process, but log a warning
            print("Attempting to process anyway, but this may fail")
        
        return file_content
    except Exception as e:
        print(f"Error fetching from S3: {str(e)}")
        # Print more detailed exception information for debugging
        import traceback
        traceback.print_exc()
        return None


def process_resources_from_db():
    """
    Get company resources from the database that have not been ingested,
    fetch them directly from S3, and process them in memory.
    """
    db = SessionLocal()
    try:
        # Get all resources that haven't been ingested yet
        resources = db.query(CompanyResource).filter(CompanyResource.is_ingested == False).all()
        print(f"Found {len(resources)} unprocessed resources")
        
        for resource in resources:
            # Get the file content directly from S3
            file_content = get_s3_file_content(resource.resource_location)
            
            if file_content:
                try:
                    # Process the file content directly
                    extract_pdf_content_to_document_db(
                        pdf_content=file_content,
                        s3_url=resource.resource_location,
                        company_id=str(resource.company_id),
                        resource_id=str(resource.id)
                    )
                    
                    # Mark the resource as ingested
                    resource.is_ingested = True
                    db.commit()
                    print(f"Resource {resource.id} marked as ingested")
                except Exception as e:
                    print(f"Error processing file content from {resource.resource_location}: {str(e)}")
                    db.rollback()
            else:
                print(f"Failed to fetch resource {resource.id} content from {resource.resource_location}")
        
    except Exception as e:
        print(f"Error processing resources: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Process resources from company_resources table
    process_resources_from_db()

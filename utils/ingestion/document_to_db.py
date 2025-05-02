import os
import uuid
from typing import List
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter

# Import database modules
from database.db import get_db, SessionLocal
from database.models import Document, Chunk, Company

load_dotenv()

# Step 1 of ingestion.
def extract_pdf_to_document_db(pdf_path: str, chunk_size: int = 1000, chunk_overlap: int = 30):
    """
    Extract content from a PDF file and store each page as a separate document.
    Then, create chunks from these documents and store them in the chunks database.
    
    Args:
        pdf_path: Path to the PDF file
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at path: {pdf_path}")
    
    print(f"Processing PDF: {pdf_path}")
    
    # Extract text from PDF
    loader = PyPDFLoader(pdf_path)
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
                company_id="0fbe6ad2-39c2-4d61-a731-9a538d907ab5",
                text=page.page_content,
                page_number=i+1,
                file_path=pdf_path
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            
            print(f"Document saved for page {i+1} with ID: {document.id}")
            
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
                    company_id="0fbe6ad2-39c2-4d61-a731-9a538d907ab5",
                    text=chunk_text
                )
                db.add(chunk)
            
            db.commit()
            print(f"Created and saved {len(text_chunks)} chunks from document {document.id} (page {i+1})")
        
    finally:
        db.close()

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


 # Example usage
    # default_pdf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "documents", "resources", "Annual Report 23-24.pdf")
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2024/accredition.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2024/Earnings call Q2'Fy25.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2024/EGM25.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2024/income_tax_matter_update.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2024/investor_meet_intimiation.pdf"

    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2024/promotor_share.pdf"

    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2024/Q2FY25.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2024/QIp-details.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2024/qip_placement.pdf"

if __name__ == "__main__":
    # 2025.
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/acquisition of shares.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/acquisition_faridabad.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/Acquisition_hospital.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/acquisition_successful.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/April25-Announcement.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/clarification_income_tax.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/earnings_call_transcript.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/increase_of_promoter_shares.pdf"

    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/IP-Q3FY25.pdf"

    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/mgs_batra_acquisition.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/press_release_Q3FY25.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/Q424 Financials.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/QIP monitoring agency Q3FY25.pdf"
    # default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/Resignation.pdf"
    default_pdf_path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/Stock News.pdf"





    # Check if path exists, otherwise use default
    pdf_path = os.environ.get("PDF_PATH", default_pdf_path)
    
    # Process a specific PDF
    if os.path.exists(pdf_path):
        extract_pdf_to_document_db(pdf_path)
    else:
        print(f"PDF not found at {pdf_path}, skipping direct extraction")
    
    # Process all documents in DB that don't have chunks
    # process_documents_to_chunks()

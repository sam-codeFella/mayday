import uuid
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

# Import database modules
from database.db import get_db, SessionLocal
from database.models import Document, Chunk, Company
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.schema.document import Document as LangchainDocument
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# here also extract all documents whose path is a match.
# then extract all chunks & contexts for those documents.
# then send them to pinecone.
def ingest_chunks_to_pinecone(exclude_path: str = "/path/to/exclude"):
    """
    Read all chunks from the database and store them in Pinecone.
    Each document in Pinecone will contain context and chunk text
    with metadata for company_id, document_id, file_path, and page_number.
    
    Args:
        exclude_path (str): Path pattern to exclude documents from ingestion
    """
    db = SessionLocal()
    try:
        # First get all document IDs that match the exclude path
        excluded_doc_ids = [
            doc.id for doc in db.query(Document)
            .filter(Document.file_path.like(f"%{exclude_path}%"))
            .all()
        ]
        
        print(f"Found {len(excluded_doc_ids)} documents to exclude based on path: {exclude_path}")
        
        # Get all chunks except those belonging to excluded documents
        chunks = db.query(Chunk).filter(
            Chunk.document_id.notin_(excluded_doc_ids) if excluded_doc_ids else True
        ).all()
        
        print(f"Found {len(chunks)} chunks in database after exclusion")

        # Initialize OpenAI embeddings
        embeddings_model = OpenAIEmbeddings(openai_api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Initialize Pinecone (ensure your Pinecone client is initialized)
        pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
        index_name = os.environ.get('PINECONE_INDEX_NAME')
        
        # Check if index exists, create if it doesn't
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=1536,  # OpenAI embedding dimension
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-west-2')
            )
        
        langchain_docs = []
        
        # Convert chunks to Langchain documents
        for i, chunk in enumerate(chunks):
            document = db.query(Document).filter(Document.id == chunk.document_id).first()
            
            if document:
                # Create content with context and chunk text
                content = f"Context: {chunk.context}\n\nContent: {chunk.text}"
                
                # Create metadata
                metadata = {
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "company_id": str(document.company_id),
                    "file_path": document.file_path or "",
                    "page_number": document.page_number or 0
                }
                
                # Create Langchain document
                langchain_doc = LangchainDocument(
                    page_content=content,
                    metadata=metadata
                )
                
                langchain_docs.append(langchain_doc)
                
                print(f"Preparing document {i+1}/{len(chunks)} for Pinecone")
            else:
                print(f"WARNING: Parent document not found for chunk {chunk.id}")
        
        # Store documents in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(langchain_docs), batch_size):
            batch = langchain_docs[i:i+batch_size]
            print(f"Storing batch {i//batch_size + 1}/{(len(langchain_docs) + batch_size - 1)//batch_size}")
            
            # Store documents in Pinecone
            PineconeVectorStore.from_documents(
                documents=batch,
                embedding=embeddings_model,
                index_name=index_name
            )
        
        print(f"Successfully stored {len(langchain_docs)} documents in Pinecone")
                
    finally:
        db.close()

if __name__ == "__main__":
    ingest_chunks_to_pinecone("/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/resources/Annual Report 23-24.pdf")

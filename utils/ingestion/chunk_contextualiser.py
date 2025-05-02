import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from sqlalchemy.orm import Session
from database.db import SessionLocal
from database.models import Document, Chunk
import argparse

load_dotenv()

# Prompt template for contextualizing chunks
CONTEXTUAL_EMBEDDING_PROMPT = """
Here is the chunk we want to situate within the whole document:
<chunk>
{chunk}
</chunk>
 
Here is the content of the whole document:
<document>
{document}
</document>
 
Please provide a short, succinct context to situate this chunk within the overall document to improve search retrieval. Respond only with the context.
"""

class ChunkContextualiser:
    """
    A class that uses Anthropic models to provide context for chunks
    based on their relation to the entire document.
    """
    
    def __init__(self, model_name: str = "claude-3-haiku-20240307"):
        """
        Initialize the ChunkContextualiser with Anthropic model.
        
        Args:
            model_name: The Anthropic model to use
        """
        self.llm = ChatAnthropic(
            model=model_name,
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            temperature=0.1,
            max_tokens=300
        )
        self.prompt_template = PromptTemplate(
            input_variables=["chunk", "document"],
            template=CONTEXTUAL_EMBEDDING_PROMPT
        )
    
    def contextualise_chunk(self, chunk_text: str, document_text: str) -> str:
        """
        Generate context for a chunk based on the entire document.
        
        Args:
            chunk_text: The text of the chunk
            document_text: The full document text
            
        Returns:
            The contextual description of the chunk
        """
        formatted_prompt = self.prompt_template.format(
            chunk=chunk_text,
            document=document_text
        )
        
        response = self.llm.invoke(formatted_prompt)
        return response.content
    
    def contextualise_chunk_by_ids(self, chunk_id: str, document_id: str, db: Session) -> Optional[str]:
        """
        Retrieve chunk and document by IDs and generate context.
        
        Args:
            chunk_id: ID of the chunk
            document_id: ID of the document
            db: Database session
            
        Returns:
            The contextual description or None if not found
        """
        chunk = db.query(Chunk).filter(Chunk.id == chunk_id).first()
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not chunk or not document:
            return None
        
        return self.contextualise_chunk(chunk.text, document.text)
    
    def process_all_chunks_for_document(self, document_id: str) -> Dict[str, str]:
        """
        Process all chunks for a given document and generate context for each.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Dictionary mapping chunk IDs to their contextual descriptions
        """
        db = SessionLocal()
        results = {}
        
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return results
            
            chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
            
            for chunk in chunks:
                context = self.contextualise_chunk(chunk.text, document.text)
                results[str(chunk.id)] = context
                
                # Update the chunk in the database with the context
                chunk.context = context
                db.commit()
                
            return results
            
        finally:
            db.close()
    
    def update_chunk_contexts_in_db(self, document_id: str) -> int:
        """
        Update the context field for all chunks in a document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Number of chunks updated
        """
        db = SessionLocal()
        count = 0
        
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return count
            
            chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
            
            for chunk in chunks:
                context = self.contextualise_chunk(chunk.text, document.text)
                # Assuming Chunk model has a 'context' field
                chunk.context = context
                count += 1
            
            db.commit()
            return count
            
        finally:
            db.close()


# query by path & add their contexts to the db.
if __name__ == "__main__":
    # Initialize contextualiser
    contextualiser = ChunkContextualiser()

    # Define the file path to search for
    path = "/Users/shams/Desktop/Panache/Cursor/aha/new_backend/utils/documents/yatharth/2025/Stock News.pdf"  # Replace this with your actual file path

    print(f"Processing documents with file path: {path}")
    db = SessionLocal()
    try:
        # Query documents with the specified file path
        documents = db.query(Document).filter(Document.file_path == path).all()
        print(f"Found {len(documents)} documents with the specified path")

        total_chunks = 0
        for document in documents:
            print(f"Processing document ID: {document.id}")
            count = contextualiser.update_chunk_contexts_in_db(str(document.id))
            total_chunks += count
            print(f"Updated {count} chunks with context for document {document.id}")

        print(f"Total: Updated {total_chunks} chunks across {len(documents)} documents")
    finally:
        db.close()

    """
    parser = argparse.ArgumentParser(description="Contextualise chunks using Anthropic")
    parser.add_argument("--document_id", type=str, help="Process a specific document by ID")
    parser.add_argument("--all", action="store_true", help="Process all documents")
    parser.add_argument("--example", action="store_true", help="Run the example")
    args = parser.parse_args()
    
    if args.document_id:
        print(f"Processing document ID: {args.document_id}")
        count = contextualiser.update_chunk_contexts_in_db(args.document_id)
        print(f"Updated {count} chunks with context")
    
    elif args.all:
        print("Processing all documents")
        db = SessionLocal()
        try:
            documents = db.query(Document).all()
            print(f"Found {len(documents)} documents")
            
            total_chunks = 0
            for document in documents:
                print(f"Processing document ID: {document.id}")
                count = contextualiser.update_chunk_contexts_in_db(str(document.id))
                total_chunks += count
                print(f"Updated {count} chunks with context for document {document.id}")
            
            print(f"Total: Updated {total_chunks} chunks across {len(documents)} documents")
        
        finally:
            db.close()
    
    
    elif args.example:
        # Test with a small example
        chunk_text = "The company's revenue increased by 15% in Q2 2023."
        document_text = 
        Annual Financial Report 2023
        
        Executive Summary:
        Our company had a strong performance in 2023 with overall growth of 12%.
        
        Quarterly Breakdown:
        Q1 2023: Revenue grew by 8% compared to previous year.
        Q2 2023: The company's revenue increased by 15% in Q2 2023.
        Q3 2023: Growth continued at 10%.
        Q4 2023: Year ended with 14% growth in Q4.
        
        Conclusion:
        The company is positioned well for 2024.
        
        
        context = contextualiser.contextualise_chunk(chunk_text, document_text)
        print(f"Generated context: {context}")
    
    else:
        parser.print_help()
    """

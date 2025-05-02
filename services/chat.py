from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from utils.ingestion.query_vector import query_vector_store

load_dotenv()

class ChatService:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-4o",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.system_prompt = """You are a helpful AI assistant that provides accurate, 
        informative, and engaging responses. Always strive to give detailed explanations 
        and cite sources when possible."""

    """
    So here we are passing all the list of messages earlier received as well. 
    Maybe this helps further in understanding the context & allows for better reasoning as well. 
    """
    async def generate_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        # Get the latest user message
        latest_user_message = None
        for msg in reversed(messages):
            if msg["role"] == "user":
                latest_user_message = msg["content"]
                break
        
        # Query vector database with the latest user question
        vector_context = []
        doc_metadata = []
        if latest_user_message:
            vector_results = query_vector_store(latest_user_message, top_k=3)
            if vector_results:
                vector_context_text = "Context from knowledge base:\n\n"
                for doc in vector_results:
                    vector_context_text += f"---\n{doc.page_content}\n---\n"
                    # Extract metadata from each document
                    doc_metadata.append({
                        "chunk_id": doc.metadata.get("chunk_id"),
                        "document_id": doc.metadata.get("document_id"),
                        "company_id": doc.metadata.get("company_id"),
                        "file_path": doc.metadata.get("file_path"),
                        "page_number": doc.metadata.get("page_number")
                    })
                vector_context.append(SystemMessage(content=vector_context_text))
        
        # Convert the messages to LangChain format
        langchain_messages = [
            SystemMessage(content=self.system_prompt)
        ]
        
        # Add vector database context if available
        if vector_context:
            langchain_messages.extend(vector_context)
        
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        # Generate response
        response = self.llm.predict_messages(langchain_messages)

        # Return both the response content and document metadata
        return {
            "content": response.content,
            "metadata": doc_metadata
        }
    
    async def create_chat_title(self, first_message: str) -> str:
        """Generate a title for a new chat based on the first message"""
        prompt = f"Generate a short, concise title (max 6 words) for a chat that starts with: {first_message}"
        messages = [
            SystemMessage(content="You are a helpful assistant that generates short, concise chat titles."),
            HumanMessage(content=prompt)
        ]
        response = self.llm.predict_messages(messages)
        return response.content.strip('"') 
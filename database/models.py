from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .db import Base

# what kind of models are these ? & what exactly is sqlalchemy ? -> seems quite awesome.
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chats = relationship("Chat", back_populates="user")
    messages = relationship("Message", back_populates="user")

#
class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat")
    votes = relationship("Vote", back_populates="chat")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    content = Column(Text)
    role = Column(String)  # 'user' or 'assistant'
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_fields = Column(JSON, nullable=True)  # Array of {file_id: string, page_number: number}
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    user = relationship("User", back_populates="messages")
    votes = relationship("Vote", back_populates="message")


class Vote(Base):
    __tablename__ = "votes"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(UUID, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(UUID, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chat = relationship("Chat", back_populates="votes")
    message = relationship("Message", back_populates="votes")

class Company(Base):
    __tablename__ = "company"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    ticker = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="company")
    chunks = relationship("Chunk", back_populates="company")
    config = relationship("CompanyConfig", back_populates="company")
    resources = relationship("CompanyResource", back_populates="company")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("company_resources.id", ondelete="CASCADE"), nullable=True)
    text = Column(Text)
    page_number = Column(Integer, nullable=True)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document")
    resource = relationship("CompanyResource", back_populates="documents")


class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text)
    context = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    company = relationship("Company", back_populates="chunks")


class CompanyConfig(Base):
    __tablename__ = "company_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False, unique=True)
    storage_location = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="config")


class CompanyResource(Base):
    __tablename__ = "company_resources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    resource_location = Column(String, nullable=False)
    source_location = Column(String, nullable=True)
    is_ingested = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="resources")
    documents = relationship("Document", back_populates="resource")


from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import Company
from uuid import UUID

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyResponse(BaseModel):
    id: UUID
    ticker: str
    name: str
    created_at: datetime

    class Config:
        orm_mode = True


@router.get("", response_model=List[CompanyResponse])
async def list_companies(
    query: str = Query(None, description="Search term for filtering companies"),
    db: Session = Depends(get_db)
):
    """
    List all companies or search companies using a query parameter
    """
    # Base query
    companies_query = db.query(Company)
    
    # Apply search filter if query is provided
    if query:
        # Search in name and ticker
        companies_query = companies_query.filter(
            (Company.name.ilike(f"%{query}%")) | 
            (Company.ticker.ilike(f"%{query}%"))
        )
    
    # Get all companies
    companies = companies_query.all()
    
    return companies


@router.get("/{company_id}/financials")
async def get_company_financials(company_id: str):
    """
    Get financial data for a specific company
    """
    # Implementation will go here
    pass


@router.get("/{company_id}/management")
async def get_company_management(company_id: str):
    """
    Get management info for a specific company
    """
    # Implementation will go here
    pass

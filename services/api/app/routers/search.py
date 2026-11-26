"""POST /search — structured and natural-language provider search endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SearchRequest as SearchRequestSchema
from app.schemas import SearchResponse
from app.search.service import execute_search

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search_providers(
    body: SearchRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    return await execute_search(body, db)

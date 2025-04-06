from fastapi import APIRouter

from .documents import router as documents_router
from .extraction import router as extraction_router
from .edit_history import router as edit_history_router
from .knowledge_base import router as knowledge_base_router

api_router = APIRouter()

api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(extraction_router, prefix="/extraction", tags=["extraction"])
api_router.include_router(edit_history_router, prefix="/edit-history", tags=["edit-history"])
api_router.include_router(knowledge_base_router, prefix="/knowledge-base", tags=["knowledge-base"]) 
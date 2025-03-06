# 导入所有模型，以便Alembic能够检测到
from .base_class import Base
from ..models.document import Document
from ..models.extraction import ExtractionResult, PhysicalStateGroup, PhysicalStateItem
from ..models.edit_history import EditHistory
from ..models.knowledge_base import KnowledgeBase 
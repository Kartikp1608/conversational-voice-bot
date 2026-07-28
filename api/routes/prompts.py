from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_db_session
from database.repositories import PromptRepository
from prompt_engine.prompt_loader import PromptLoader

router = APIRouter(prefix="/prompts", tags=["Prompts"])


class PromptCreateRequest(BaseModel):
    prompt_id: str = Field(..., description="Unique prompt ID (e.g. sales_outbound)")
    name: str = Field(..., description="Human readable prompt name")
    content_yaml: str = Field(..., description="Full YAML prompt specification")
    description: str = Field("", description="Optional prompt description")


@router.post("/", status_code=201)
async def create_or_update_prompt(req: PromptCreateRequest, db: AsyncSession = Depends(get_db_session)):
    """Upload or update dynamic business YAML system prompt."""
    repo = PromptRepository(db)
    tmpl = await repo.save_prompt(
        prompt_id=req.prompt_id,
        name=req.name,
        content_yaml=req.content_yaml,
        description=req.description,
    )
    return {"status": "saved", "prompt_id": tmpl.id, "version": tmpl.version}


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: str):
    """Retrieve prompt YAML specification."""
    loader = PromptLoader()
    data = loader.load_prompt(prompt_id)
    return data

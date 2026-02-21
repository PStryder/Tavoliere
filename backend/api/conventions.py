"""Convention template CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.deps import get_current_identity, require_admin
from backend.auth.models import TokenPayload
from backend.engine.conventions import (
    create_convention,
    delete_convention,
    get_convention,
    list_conventions,
    update_convention,
)
from backend.models.convention import ConventionCreate, ConventionUpdate

router = APIRouter(prefix="/api/conventions", tags=["conventions"])


@router.get("")
async def get_conventions(
    _: TokenPayload = Depends(get_current_identity),
):
    """List all convention templates."""
    return [c.model_dump(mode="json") for c in list_conventions()]


@router.get("/{template_id}")
async def get_convention_by_id(
    template_id: str,
    _: TokenPayload = Depends(get_current_identity),
):
    """Get a single convention template."""
    template = get_convention(template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template.model_dump(mode="json")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_new_convention(
    req: ConventionCreate,
    _: TokenPayload = Depends(require_admin),
):
    """Create a custom convention template (admin only)."""
    return create_convention(req).model_dump(mode="json")


@router.put("/{template_id}")
async def update_convention_by_id(
    template_id: str,
    updates: ConventionUpdate,
    _: TokenPayload = Depends(require_admin),
):
    """Update a custom convention template (admin only, cannot edit built-in)."""
    template = update_convention(template_id, updates)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or is built-in",
        )
    return template.model_dump(mode="json")


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_convention_by_id(
    template_id: str,
    _: TokenPayload = Depends(require_admin),
):
    """Delete a custom convention template (admin only, cannot delete built-in)."""
    if not delete_convention(template_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or is built-in",
        )

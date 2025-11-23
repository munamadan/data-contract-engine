from fastapi import APIRouter, HTTPException, Path
from app.models.schemas import ContractTemplate, ContractTemplateList
from app.utils.contract_templates import get_all_templates, get_template_by_name
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/contracts/templates",
    tags=["templates"],
)


@router.get("/", response_model=ContractTemplateList)
def list_templates():
    logger.info("GET /contracts/templates")
    
    templates = get_all_templates()
    
    return ContractTemplateList(
        templates=templates,
        total=len(templates)
    )


@router.get("/{template_name}", response_model=ContractTemplate)
def get_template(
    template_name: str = Path(..., description="Template name")
):
    logger.info(f"GET /contracts/templates/{template_name}")
    
    template = get_template_by_name(template_name)
    
    if not template:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "TemplateNotFoundError",
                "message": f"Template '{template_name}' not found"
            }
        )
    
    return template
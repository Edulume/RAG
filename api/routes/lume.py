"""
Lume API Endpoints - Structure and Content Generation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import logging
from typing import Dict
import json
import xml.etree.ElementTree as ET
import re

from keiz.lume.models import (
    StructureGenerationRequest,
    StructureGenerationResponse,
    StructureApprovalRequest,
    ContentGenerationStatus,
    ContentRegenerationRequest
)
from keiz.lume.structure_generator import generate_course_structure, validate_structure_json, validate_structure_xml
from keiz.lume.generators.content_generator import (
    generate_course_content,
    regenerate_content
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/lume", tags=["lume"])

# In-memory storage for structures (replace with database in production)
structures_db: Dict[str, Dict] = {}


def parse_json_structure(structure_data: Dict, metadata: Dict) -> Dict:
    """Parse JSON structure into format expected by content generator (LMS schema)"""
    modules = []

    for module in structure_data.get("modules", []):
        sections = []

        for section in module.get("sections", []):
            subsections = []

            for subsection in section.get("subsections", []):
                subsections.append({
                    "subsection_id": str(subsection.get("id")),
                    "title": subsection.get("title", ""),
                    "type": subsection.get("type", "content"),
                    "bloom_level": subsection.get("bloom_level", "remember"),
                    "learning_objectives": subsection.get("learning_objectives", [
                        f"Understand {subsection.get('title', 'the topic').lower()}",
                        f"Apply concepts of {subsection.get('title', 'the topic').lower()}"
                    ])
                })

            sections.append({
                "section_id": str(section.get("id")),
                "title": section.get("title", ""),
                "description": section.get("description", ""),
                "subsections": subsections
            })

        modules.append({
            "module_number": module.get("id"),
            "title": module.get("title", ""),
            "overview": module.get("description", ""),
            "sections": sections
        })

    return {
        "structure": {"modules": modules},
        "metadata": metadata
    }


def parse_xml_structure(structure_xml: str, metadata: Dict) -> Dict:
    """Parse XML structure into format expected by content generator (DEPRECATED)"""
    # Remove markdown code fences if present
    xml_content = structure_xml
    if xml_content.startswith("```xml"):
        xml_content = xml_content.replace("```xml\n", "").replace("```", "").strip()

    # Wrap in root element for parsing
    xml_with_root = f"<root>{xml_content}</root>"
    root = ET.fromstring(xml_with_root)

    modules = []

    for module_elem in root.findall("MODULE"):
        module_id = module_elem.get("id")
        module_title = module_elem.find("MODULE_TITLE").text if module_elem.find("MODULE_TITLE") is not None else ""
        module_desc = module_elem.find("MODULE_DESCRIPTION").text if module_elem.find("MODULE_DESCRIPTION") is not None else ""

        submodules = []

        for submod_elem in module_elem.findall("SUBMODULE"):
            submod_id = submod_elem.get("id")
            submod_title = submod_elem.find("SUBMODULE_TITLE").text if submod_elem.find("SUBMODULE_TITLE") is not None else ""
            submod_type = submod_elem.find("SUBMODULE_TYPE").text if submod_elem.find("SUBMODULE_TYPE") is not None else ""
            bloom_level = submod_elem.find("BLOOM_LEVEL").text if submod_elem.find("BLOOM_LEVEL") is not None else ""

            # Create learning objectives based on Bloom level and title
            learning_objectives = [
                f"Understand {submod_title.lower()}",
                f"Apply concepts of {submod_title.lower()}"
            ]

            submodules.append({
                "submodule_id": submod_id,
                "title": submod_title,
                "type": submod_type,
                "bloom_level": bloom_level,
                "learning_objectives": learning_objectives
            })

        modules.append({
            "module_number": int(module_id),
            "title": module_title,
            "overview": module_desc,
            "submodules": submodules
        })

    return {
        "structure": {"modules": modules},
        "metadata": metadata
    }


@router.post("/generate-structure", response_model=StructureGenerationResponse)
async def create_structure(request: StructureGenerationRequest):
    """
    Generate a course structure using filtered RAG + LLM

    This endpoint:
    1. Validates content availability
    2. Retrieves relevant textbook context via filtered RAG
    3. Generates XML structure using LLM
    4. Returns structure_id for approval workflow

    Example (New LMS Format):
        POST /api/v1/lume/generate-structure
        {
            "structure": {
                "modules": 2
            },
            "subject": "Science",
            "prompt": "Create a course on Atoms and Molecules",
            "gradeLevel": "9th Grade"
        }

    Example (Legacy Format):
        POST /api/v1/lume/generate-structure
        {
            "board": "CBSE",
            "class_num": 9,
            "subject": "English",
            "prompt": "Create a course for Chapter 1: The Fun They Had",
            "chapter_number": 1,
            "k": 10
        }
    """
    try:
        # Extract module count from new LMS format if provided
        module_count = None
        if request.structure is not None:
            module_count = request.structure.modules
            logger.info(f"New LMS format: {module_count} modules requested")

        # Parse gradeLevel or use class_num (backward compatible)
        class_num = request.class_num
        if class_num is None and request.gradeLevel:
            # Extract numeric grade from gradeLevel (e.g., "9th Grade" -> 9)
            match = re.search(r'(\d+)', request.gradeLevel)
            if match:
                class_num = int(match.group(1))
                logger.info(f"Extracted class {class_num} from gradeLevel '{request.gradeLevel}'")
            else:
                class_num = 9  # Default fallback
                logger.warning(f"Could not parse gradeLevel '{request.gradeLevel}', defaulting to class 9")
        elif class_num is None:
            class_num = 9  # Default to class 9
            logger.info("No class_num or gradeLevel provided, defaulting to class 9")

        logger.info(f"Structure generation request: {request.board} Class {class_num} {request.subject}")

        # Generate the structure
        result = generate_course_structure(
            board=request.board,
            class_num=class_num,
            subject=request.subject,
            prompt=request.prompt,
            chapter_number=request.chapter_number,
            k=request.k,
            module_count=module_count
        )

        # Validate the structure (JSON or XML based on format)
        structure_format = result['metadata'].get('format', 'xml')

        if structure_format == 'json':
            validation = validate_structure_json(result['structure'])
        else:
            # Fallback to XML validation for backward compatibility
            validation = validate_structure_xml(result.get('structure_xml', ''))

        if not validation['valid']:
            logger.error(f"Generated invalid structure: {validation['errors']}")
            raise HTTPException(
                status_code=500,
                detail=f"Generated invalid structure: {validation['errors']}"
            )

        if validation['warnings']:
            logger.warning(f"Structure warnings: {validation['warnings']}")
            result['metadata']['warnings'] = validation['warnings']

        # Store in memory (replace with database later)
        structure_id = result['structure_id']
        structures_db[structure_id] = result

        logger.info(f"Structure {structure_id} created successfully")

        return StructureGenerationResponse(**result)

    except ValueError as e:
        # Content not available error
        logger.error(f"Content availability error: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # LLM or other errors
        logger.error(f"Structure generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Structure generation failed: {str(e)}")


@router.get("/structure/{structure_id}")
async def get_structure(structure_id: str):
    """
    Retrieve a generated structure by ID

    Example:
        GET /api/v1/lume/structure/str_abc123
    """
    if structure_id not in structures_db:
        raise HTTPException(status_code=404, detail=f"Structure {structure_id} not found")

    return structures_db[structure_id]


@router.post("/structure/{structure_id}/approve")
async def approve_structure(structure_id: str, request: StructureApprovalRequest):
    """
    Approve or reject a generated structure

    Example:
        POST /api/v1/lume/structure/str_abc123/approve
        {
            "approved": true,
            "feedback": "Looks great!"
        }
    """
    if structure_id not in structures_db:
        raise HTTPException(status_code=404, detail=f"Structure {structure_id} not found")

    structure = structures_db[structure_id]

    if request.approved:
        structure['status'] = 'approved'
        logger.info(f"Structure {structure_id} approved")
        message = "Structure approved! Ready for content generation."
    else:
        structure['status'] = 'rejected'
        structure['metadata']['rejection_feedback'] = request.feedback
        logger.info(f"Structure {structure_id} rejected: {request.feedback}")
        message = "Structure rejected. Provide new prompt to regenerate."

    return {
        "structure_id": structure_id,
        "status": structure['status'],
        "message": message,
        "feedback": request.feedback
    }


@router.get("/structure/{structure_id}/status", response_model=ContentGenerationStatus)
async def get_generation_status(structure_id: str):
    """
    Get the status of content generation for a structure

    Example:
        GET /api/v1/lume/structure/str_abc123/status
    """
    if structure_id not in structures_db:
        raise HTTPException(status_code=404, detail=f"Structure {structure_id} not found")

    structure = structures_db[structure_id]

    # For now, return basic status
    # In Phase 8, this will track actual content generation progress
    status = ContentGenerationStatus(
        structure_id=structure_id,
        status=structure['status'],
        progress=0,
        current_module=None,
        completed_submodules=0,
        total_submodules=12
    )

    return status


@router.delete("/structure/{structure_id}")
async def delete_structure(structure_id: str):
    """
    Delete a structure from memory

    Example:
        DELETE /api/v1/lume/structure/str_abc123
    """
    if structure_id not in structures_db:
        raise HTTPException(status_code=404, detail=f"Structure {structure_id} not found")

    del structures_db[structure_id]
    logger.info(f"Structure {structure_id} deleted")

    return {"message": f"Structure {structure_id} deleted successfully"}


# ============================================================================
# Content Generation Endpoints (Phase 8B)
# ============================================================================

@router.post("/structure/{structure_id}/generate-content")
async def start_content_generation(structure_id: str, background_tasks: BackgroundTasks):
    """
    Start content generation for an approved course structure.

    This endpoint:
    1. Validates structure is approved
    2. Starts background content generation task
    3. Returns immediately with generation_id
    4. Use /content-stream endpoint to monitor progress

    Example:
        POST /api/v1/lume/structure/str_abc123/generate-content
    """
    if structure_id not in structures_db:
        raise HTTPException(status_code=404, detail=f"Structure {structure_id} not found")

    structure = structures_db[structure_id]

    # Validate structure is approved
    if structure.get('status') != 'approved':
        raise HTTPException(
            status_code=400,
            detail=f"Structure must be approved before content generation. Current status: {structure.get('status')}"
        )

    # Update status
    structure['status'] = 'generating_content'
    structure['content_generation_started_at'] = json.dumps({"timestamp": "now"})

    logger.info(f"Starting content generation for structure {structure_id}")

    return {
        "structure_id": structure_id,
        "status": "generating_content",
        "message": "Content generation started. Use /content-stream endpoint to monitor progress.",
        "stream_url": f"/api/v1/lume/structure/{structure_id}/content-stream"
    }


@router.get("/structure/{structure_id}/content-stream")
async def stream_content_generation(structure_id: str):
    """
    SSE endpoint for real-time content generation progress.

    Streams progress events as content is generated:
    - module_start
    - submodule_start
    - section_start
    - section_complete
    - submodule_complete
    - module_complete
    - complete

    Example:
        GET /api/v1/lume/structure/str_abc123/content-stream

    Events:
        data: {"event": "section_complete", "module": 1, "submodule": 1, "section": "reading", "progress": 8}
    """
    if structure_id not in structures_db:
        raise HTTPException(status_code=404, detail=f"Structure {structure_id} not found")

    structure = structures_db[structure_id]

    async def event_generator():
        """Generate SSE events for content generation progress"""
        try:
            # Parse structure based on format
            structure_format = structure.get("metadata", {}).get("format", "xml")

            if structure_format == "json":
                parsed_structure = parse_json_structure(
                    structure.get("structure", {}),
                    structure.get("metadata", {})
                )
            else:
                # Fallback to XML for backward compatibility
                parsed_structure = parse_xml_structure(
                    structure.get("structure_xml", ""),
                    structure.get("metadata", {})
                )

            # Generate content with streaming
            async for event in generate_course_content(parsed_structure):
                # Format as SSE
                event_data = json.dumps(event)
                yield f"data: {event_data}\n\n"

                # If complete, update structure and break
                if event.get("event") == "complete":
                    # Store generated content
                    structure['content'] = {"modules": event.get("modules", [])}
                    structure['status'] = 'content_complete'
                    structure['content_generated_at'] = json.dumps({"timestamp": "now"})
                    logger.info(f"Content generation complete for {structure_id}")
                    break

        except Exception as e:
            logger.error(f"Content generation error for {structure_id}: {e}")
            structure['status'] = 'content_generation_failed'
            structure['content_generation_error'] = str(e)
            error_event = json.dumps({
                "event": "error",
                "error": str(e)
            })
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/structure/{structure_id}/regenerate")
async def regenerate_content_endpoint(
    structure_id: str,
    request: ContentRegenerationRequest
):
    """
    Regenerate specific section/submodule/module content.

    Granularity levels:
    - section: Regenerate single section (e.g., "1.1.reading")
    - submodule: Regenerate all sections in submodule (e.g., "1.1")
    - module: Regenerate all submodules in module (e.g., "2")

    Example (section):
        POST /api/v1/lume/structure/str_abc123/regenerate
        {
            "target_type": "section",
            "target_path": "1.1.reading",
            "feedback": "Too technical, simplify the language"
        }

    Example (submodule):
        POST /api/v1/lume/structure/str_abc123/regenerate
        {
            "target_type": "submodule",
            "target_path": "1.1",
            "feedback": "Add more examples"
        }

    Example (module):
        POST /api/v1/lume/structure/str_abc123/regenerate
        {
            "target_type": "module",
            "target_path": "2",
            "feedback": "Needs better engagement activities"
        }
    """
    if structure_id not in structures_db:
        raise HTTPException(status_code=404, detail=f"Structure {structure_id} not found")

    structure = structures_db[structure_id]

    # Validate content exists
    if 'content' not in structure:
        raise HTTPException(
            status_code=400,
            detail="No content to regenerate. Generate content first."
        )

    try:
        # Regenerate the specified content
        result = await regenerate_content(
            course_structure=structure,
            target_type=request.target_type,
            target_path=request.target_path,
            feedback=request.feedback
        )

        # Update the structure with regenerated content
        regenerated = result["regenerated_content"]
        target_type = result["target_type"]
        target_path = result["target_path"]

        # Parse path and update appropriate location
        if target_type == "section":
            parts = target_path.split(".")
            module_num = int(parts[0])
            submodule_num = int(parts[1])
            section_type = parts[2]

            # Find and update the section
            modules = structure['content'].get('modules', [])
            for module in modules:
                if module.get('module_number') == module_num:
                    submodules = module.get('submodules', [])
                    if submodule_num - 1 < len(submodules):
                        submodule = submodules[submodule_num - 1]
                        sections = submodule.get('sections', [])
                        for i, section in enumerate(sections):
                            if section.get('section_type') == section_type:
                                sections[i] = regenerated
                                break

        elif target_type == "submodule":
            parts = target_path.split(".")
            module_num = int(parts[0])
            submodule_num = int(parts[1])

            # Find and update the submodule
            modules = structure['content'].get('modules', [])
            for module in modules:
                if module.get('module_number') == module_num:
                    submodules = module.get('submodules', [])
                    if submodule_num - 1 < len(submodules):
                        submodules[submodule_num - 1] = regenerated

        elif target_type == "module":
            module_num = int(target_path)

            # Find and update the module
            modules = structure['content'].get('modules', [])
            for i, module in enumerate(modules):
                if module.get('module_number') == module_num:
                    modules[i] = regenerated

        # Update status
        structure['status'] = 'content_regenerated'

        # Track regeneration history
        if 'regeneration_history' not in structure:
            structure['regeneration_history'] = []

        from datetime import datetime
        structure['regeneration_history'].append({
            "target_type": target_type,
            "target_path": target_path,
            "feedback": request.feedback,
            "regenerated_at": datetime.utcnow().isoformat()
        })

        logger.info(f"Regenerated {target_type} at {target_path} for {structure_id}")

        return {
            "structure_id": structure_id,
            "status": structure['status'],
            "message": f"Successfully regenerated {target_type} at {target_path}",
            "regenerated": result
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Regeneration error: {e}")
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")

"""
Assessment API Routes
Handles assessment generation, retrieval, and management
"""

import logging
from fastapi import APIRouter, HTTPException

from keiz.lume.models import AssessmentGenerationRequest, AssessmentGenerationResponse
from keiz.lume.generators.assessment_generator import generate_assessment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/lume/assessment")

# In-memory storage for assessments (replace with database in production)
assessments_db = {}


@router.post("/generate", response_model=AssessmentGenerationResponse)
async def create_assessment(request: AssessmentGenerationRequest):
    """
    Generate a new assessment with specified question type and count

    Question types:
    - mcq: Multiple Choice Questions (4 options)
    - true_false: True/False statements
    - fill_blanks: Fill in the blanks
    - match: Match the following
    - one_word: One-word answers
    - mixed: Combination of all types
    """
    try:
        logger.info(f"Assessment generation request: {request.board} Class {request.class_num} {request.subject}")
        logger.info(f"Type: {request.question_type}, Count: {request.question_count}")

        # Generate assessment
        assessment_data = generate_assessment(
            board=request.board,
            class_num=request.class_num,
            subject=request.subject,
            topic=request.topic,
            question_type=request.question_type,
            question_count=request.question_count,
            marks_per_question=request.marks_per_question,
            difficulty=request.difficulty,
            k=request.k
        )

        # Store in memory
        assessment_id = assessment_data['assessment_id']
        assessments_db[assessment_id] = assessment_data

        logger.info(f"Assessment {assessment_id} created successfully")

        return AssessmentGenerationResponse(**assessment_data)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Assessment generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Assessment generation failed: {str(e)}")


@router.get("/{assessment_id}")
async def get_assessment(assessment_id: str):
    """Retrieve an assessment by ID"""
    if assessment_id not in assessments_db:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")

    return assessments_db[assessment_id]


@router.delete("/{assessment_id}")
async def delete_assessment(assessment_id: str):
    """Delete an assessment"""
    if assessment_id not in assessments_db:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")

    del assessments_db[assessment_id]
    return {"message": f"Assessment {assessment_id} deleted successfully"}


@router.get("/")
async def list_assessments():
    """List all generated assessments"""
    return {
        "count": len(assessments_db),
        "assessments": [
            {
                "assessment_id": aid,
                "type": data.get("type"),
                "metadata": data.get("metadata"),
                "created_at": data.get("created_at")
            }
            for aid, data in assessments_db.items()
        ]
    }


@router.post("/{assessment_id}/approve")
async def approve_assessment(assessment_id: str, approval_data: dict):
    """
    Approve or reject an assessment

    Example:
        POST /api/v1/lume/assessment/asm_abc123/approve
        {
            "approved": true,
            "feedback": "Looks good!"
        }
    """
    if assessment_id not in assessments_db:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")

    assessment = assessments_db[assessment_id]
    approved = approval_data.get("approved", False)
    feedback = approval_data.get("feedback", "")

    # Update status
    if approved:
        assessment["status"] = "approved"
        logger.info(f"Assessment {assessment_id} approved")
    else:
        assessment["status"] = "rejected"
        logger.info(f"Assessment {assessment_id} rejected: {feedback}")

    # Add approval metadata
    from datetime import datetime
    assessment["approval_metadata"] = {
        "approved": approved,
        "feedback": feedback,
        "reviewed_at": datetime.utcnow().isoformat()
    }

    return {
        "assessment_id": assessment_id,
        "status": assessment["status"],
        "message": "Assessment approved" if approved else "Assessment rejected",
        "feedback": feedback
    }


@router.post("/{assessment_id}/regenerate")
async def regenerate_assessment_question(assessment_id: str, regen_data: dict):
    """
    Regenerate a specific question in the assessment

    Example:
        POST /api/v1/lume/assessment/asm_abc123/regenerate
        {
            "question_number": 3,
            "feedback": "Make this question easier and more clear"
        }
    """
    if assessment_id not in assessments_db:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")

    assessment = assessments_db[assessment_id]
    question_number = regen_data.get("question_number")
    feedback = regen_data.get("feedback", "")

    if not question_number:
        raise HTTPException(status_code=400, detail="question_number is required")

    # Find the question
    questions = assessment["structure"].get("questions", [])
    if question_number < 1 or question_number > len(questions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid question_number. Must be between 1 and {len(questions)}"
        )

    # Update status to regenerating
    assessment["status"] = "regenerating"

    logger.info(f"Regenerating question {question_number} for assessment {assessment_id}")
    logger.info(f"Feedback: {feedback}")

    # TODO: Implement actual regeneration logic
    # For now, we'll just mark it and add to feedback history
    if "regeneration_history" not in assessment:
        assessment["regeneration_history"] = []

    from datetime import datetime
    assessment["regeneration_history"].append({
        "question_number": question_number,
        "feedback": feedback,
        "regenerated_at": datetime.utcnow().isoformat()
    })

    # After regeneration (placeholder - would call LLM here)
    assessment["status"] = "pending_approval"

    return {
        "assessment_id": assessment_id,
        "status": assessment["status"],
        "message": f"Question {question_number} will be regenerated",
        "feedback": feedback,
        "note": "Regeneration logic pending implementation"
    }

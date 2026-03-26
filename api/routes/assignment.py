"""
Assignment API Endpoints
"""

from fastapi import APIRouter, HTTPException
import logging
from typing import Dict

from keiz.lume.models import (
    AssignmentGenerationRequest,
    AssignmentGenerationResponse
)
from keiz.lume.generators.assignment_generator import generate_assignment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/lume/assignment", tags=["lume-assignment"])

# In-memory storage (replace with database in production)
assignments_db: Dict[str, Dict] = {}


@router.post("/generate", response_model=AssignmentGenerationResponse)
async def create_assignment(request: AssignmentGenerationRequest):
    """
    Generate a practice assignment with specified question type

    Supports:
    - Long answer questions (5-10 marks, apply/analyze/evaluate)
    - Short answer questions (2-3 marks, understand/apply)
    - Numerical problems (with step-by-step solutions)
    - Mixed assignments (combination of types)

    Example:
        POST /api/v1/lume/assignment/generate
        {
            "board": "CBSE",
            "class_num": 9,
            "subject": "Mathematics",
            "topic": "Polynomial Division - Practice",
            "question_type": "long_answer",
            "question_count": 5,
            "marks_per_question": 5,
            "difficulty": "medium",
            "k": 10
        }
    """
    try:
        logger.info(f"Assignment generation request: {request.board} Class {request.class_num} {request.subject}")
        logger.info(f"Type: {request.question_type}, Count: {request.question_count}")

        # Generate the assignment
        result = generate_assignment(
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
        assignment_id = result['assignment_id']
        assignments_db[assignment_id] = result

        logger.info(f"Assignment {assignment_id} created successfully")

        return AssignmentGenerationResponse(**result)

    except ValueError as e:
        logger.error(f"Content availability error: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Assignment generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Assignment generation failed: {str(e)}")


@router.get("/{assignment_id}")
async def get_assignment(assignment_id: str):
    """
    Retrieve a generated assignment by ID

    Example:
        GET /api/v1/lume/assignment/asn_abc123
    """
    if assignment_id not in assignments_db:
        raise HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found")

    return assignments_db[assignment_id]


@router.delete("/{assignment_id}")
async def delete_assignment(assignment_id: str):
    """
    Delete an assignment from memory

    Example:
        DELETE /api/v1/lume/assignment/asn_abc123
    """
    if assignment_id not in assignments_db:
        raise HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found")

    del assignments_db[assignment_id]
    logger.info(f"Assignment {assignment_id} deleted")

    return {"message": f"Assignment {assignment_id} deleted successfully"}


@router.post("/{assignment_id}/approve")
async def approve_assignment(assignment_id: str, approval_data: Dict):
    """
    Approve or reject an assignment

    Example:
        POST /api/v1/lume/assignment/asn_abc123/approve
        {
            "approved": true,
            "feedback": "Looks good!"
        }
    """
    if assignment_id not in assignments_db:
        raise HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found")

    assignment = assignments_db[assignment_id]
    approved = approval_data.get("approved", False)
    feedback = approval_data.get("feedback", "")

    # Update status
    if approved:
        assignment["status"] = "approved"
        logger.info(f"Assignment {assignment_id} approved")
    else:
        assignment["status"] = "rejected"
        logger.info(f"Assignment {assignment_id} rejected: {feedback}")

    # Add approval metadata
    from datetime import datetime
    assignment["approval_metadata"] = {
        "approved": approved,
        "feedback": feedback,
        "reviewed_at": datetime.utcnow().isoformat()
    }

    return {
        "assignment_id": assignment_id,
        "status": assignment["status"],
        "message": "Assignment approved" if approved else "Assignment rejected",
        "feedback": feedback
    }


@router.post("/{assignment_id}/regenerate")
async def regenerate_question(assignment_id: str, regen_data: Dict):
    """
    Regenerate a specific question in the assignment

    Example:
        POST /api/v1/lume/assignment/asn_abc123/regenerate
        {
            "question_number": 3,
            "feedback": "Make this question easier and more clear"
        }
    """
    if assignment_id not in assignments_db:
        raise HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found")

    assignment = assignments_db[assignment_id]
    question_number = regen_data.get("question_number")
    feedback = regen_data.get("feedback", "")

    if not question_number:
        raise HTTPException(status_code=400, detail="question_number is required")

    # Find the question
    questions = assignment["structure"].get("questions", [])
    if question_number < 1 or question_number > len(questions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid question_number. Must be between 1 and {len(questions)}"
        )

    # Update status to regenerating
    assignment["status"] = "regenerating"

    logger.info(f"Regenerating question {question_number} for assignment {assignment_id}")
    logger.info(f"Feedback: {feedback}")

    # TODO: Implement actual regeneration logic
    # For now, we'll just mark it and add to feedback history
    if "regeneration_history" not in assignment:
        assignment["regeneration_history"] = []

    from datetime import datetime
    assignment["regeneration_history"].append({
        "question_number": question_number,
        "feedback": feedback,
        "regenerated_at": datetime.utcnow().isoformat()
    })

    # After regeneration (placeholder - would call LLM here)
    assignment["status"] = "pending_approval"

    return {
        "assignment_id": assignment_id,
        "status": assignment["status"],
        "message": f"Question {question_number} will be regenerated",
        "feedback": feedback,
        "note": "Regeneration logic pending implementation"
    }

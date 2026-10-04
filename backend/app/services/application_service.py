from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc
from fastapi import HTTPException, status
from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.models.profile import CandidateProfile
from app.schemas.application import ApplicationCreate, ApplicationListResponse, ApplicationResponse
from typing import Optional


def get_applications(db: Session, skip: int = 0, limit: int = 50, status: Optional[str] = None) -> ApplicationListResponse:
    query = db.query(Application)
    if status:
        query = query.filter(Application.status == status)

    total = query.count()
    items = query.order_by(desc(Application.updated_at)).offset(skip).limit(limit).all()

    return ApplicationListResponse(
        items=[ApplicationResponse.model_validate(item) for item in items],
        total=total
    )


def create_application(db: Session, data: ApplicationCreate) -> Application:
    # Foreign key validation
    if data.job_id:
        job_exists = db.query(Job).filter(Job.id == data.job_id).first()
        if not job_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID '{data.job_id}' not found."
            )

    if data.candidate_id:
        candidate_exists = db.query(CandidateProfile).filter(CandidateProfile.id == data.candidate_id).first()
        if not candidate_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{data.candidate_id}' not found."
            )

    app = Application(**data.model_dump())
    db.add(app)
    try:
        db.flush()

        # Create initial audit event
        event = ApplicationEvent(
            application_id=app.id,
            event_type="application_created",
            description="Application record created in foundation",
            event_metadata={"initial_status": app.status}
        )
        db.add(event)
        db.commit()
        db.refresh(app)
        return app
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity error: {str(e.orig)}"
        )

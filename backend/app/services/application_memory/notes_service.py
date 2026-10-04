from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.application import Application, ApplicationNote, ApplicationEvent
from app.services.application_memory.models import NoteCategory


class NotesService:
    """
    Step 10: Append-only Application Notes Service.
    Allows candidate to attach timestamped observations, recruiter notes,
    and interview reflections without overwriting previous entries.
    """

    @staticmethod
    def add_note(
        db: Session,
        application_id: str,
        content: str,
        category: str = NoteCategory.GENERAL.value,
        author: str = "candidate",
    ) -> ApplicationNote:
        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Note content cannot be empty.",
            )

        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' not found.",
            )

        valid_categories = {c.value for c in NoteCategory}
        if category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid note category '{category}'. Valid options: {sorted(valid_categories)}",
            )

        note = ApplicationNote(
            application_id=app.id,
            author=author,
            category=category,
            content=content.strip(),
        )
        db.add(note)
        db.flush()

        event = ApplicationEvent(
            application_id=app.id,
            event_type="USER_NOTE_ADDED",
            description=f"User note added in category '{category}'.",
            actor="user",
            provenance="USER_CONFIRMED",
            event_metadata={
                "note_id": note.id,
                "category": category,
                "author": author,
                "snippet": content[:80] + ("..." if len(content) > 80 else ""),
            },
        )
        db.add(event)
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def get_notes(db: Session, application_id: str) -> List[ApplicationNote]:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' not found.",
            )
        return (
            db.query(ApplicationNote)
            .filter_by(application_id=application_id)
            .order_by(ApplicationNote.created_at.desc())
            .all()
        )

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.profile import (
    CandidateProfileResponse,
    CandidateProfileCreate,
    CandidateProfileUpdate,
    CandidatePreferenceResponse,
    CandidatePreferenceUpdate,
    EducationResponse,
    EducationCreate,
    EducationUpdate,
    ExperienceResponse,
    ExperienceCreate,
    ExperienceUpdate,
    SkillResponse,
    SkillCreate,
    SkillUpdate,
    ProjectResponse,
    ProjectCreate,
    ProjectUpdate,
    CertificationResponse,
    CertificationCreate,
    CertificationUpdate,
    DocumentResponse,
    DocumentCreate,
    ProfileCompletenessResponse,
    ResumeIngestResponse
)
from app.services.profile_service import (
    get_default_profile,
    create_or_update_profile,
    partial_update_profile,
    calculate_profile_completeness,
    get_preferences,
    update_preferences,
    get_educations,
    create_education,
    update_education,
    delete_education,
    get_experiences,
    create_experience,
    update_experience,
    delete_experience,
    get_skills,
    create_skill,
    update_skill,
    delete_skill,
    get_projects,
    create_project,
    update_project,
    delete_project,
    get_certifications,
    create_certification,
    update_certification,
    delete_certification,
    get_documents,
    create_document,
    delete_document,
    ingest_resume_pipeline
)
from typing import Optional, List

router = APIRouter()


# ==========================================
# Candidate Profile Core Endpoints
# ==========================================
@router.get("/profile", response_model=Optional[CandidateProfileResponse])
def get_profile(db: Session = Depends(get_db)):
    profile = get_default_profile(db)
    if not profile:
        return None
    # Attach completeness
    completeness = calculate_profile_completeness(profile)
    res = CandidateProfileResponse.model_validate(profile)
    res.completeness = completeness
    return res


@router.post("/profile", response_model=CandidateProfileResponse, status_code=status.HTTP_200_OK)
def save_profile(data: CandidateProfileCreate, db: Session = Depends(get_db)):
    try:
        profile = create_or_update_profile(db, data)
        completeness = calculate_profile_completeness(profile)
        res = CandidateProfileResponse.model_validate(profile)
        res.completeness = completeness
        return res
    except HTTPException:
        raise
    except Exception as e:
        from app.core.logging import logger
        logger.error(f"Failed to save profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to save profile. Please check the submitted data for errors."
        )


@router.patch("/profile", response_model=CandidateProfileResponse, status_code=status.HTTP_200_OK)
def patch_profile(data: CandidateProfileUpdate, db: Session = Depends(get_db)):
    try:
        profile = partial_update_profile(db, data)
        completeness = calculate_profile_completeness(profile)
        res = CandidateProfileResponse.model_validate(profile)
        res.completeness = completeness
        return res
    except HTTPException:
        raise
    except Exception as e:
        from app.core.logging import logger
        logger.error(f"Failed to update profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update profile. Please check the submitted data for errors."
        )


@router.get("/profile/completeness", response_model=ProfileCompletenessResponse)
def get_profile_completeness_endpoint(db: Session = Depends(get_db)):
    profile = get_default_profile(db)
    return calculate_profile_completeness(profile)


# ==========================================
# Career Preferences Endpoints
# ==========================================
@router.get("/profile/preferences", response_model=CandidatePreferenceResponse)
def get_candidate_preferences(db: Session = Depends(get_db)):
    pref = get_preferences(db)
    return pref


@router.put("/profile/preferences", response_model=CandidatePreferenceResponse)
def put_candidate_preferences(data: CandidatePreferenceUpdate, db: Session = Depends(get_db)):
    return update_preferences(db, data)


@router.patch("/profile/preferences", response_model=CandidatePreferenceResponse)
def patch_candidate_preferences(data: CandidatePreferenceUpdate, db: Session = Depends(get_db)):
    return update_preferences(db, data)


# ==========================================
# Resume Ingestion Pipeline Endpoint
# ==========================================
@router.post("/profile/resume/ingest", response_model=ResumeIngestResponse)
async def ingest_resume(
    file: Optional[UploadFile] = None,
    db: Session = Depends(get_db)
):
    try:
        source_bytes = None
        if file is not None:
            filename = file.filename or ""
            if not filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file type. Only PDF (.pdf) documents are permitted for resume ingestion."
                )
            source_bytes = await file.read()
            if len(source_bytes) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded resume exceeds maximum allowed size of 10 MB."
                )
        return ingest_resume_pipeline(db, source_bytes)
    except HTTPException:
        raise
    except Exception as e:
        from app.core.logging import logger
        logger.error(f"Resume ingestion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume ingestion failed. Please verify that the file is a valid, uncorrupted PDF document."
        )


# ==========================================
# Education Endpoints
# ==========================================
@router.get("/profile/educations", response_model=List[EducationResponse])
def list_educations(db: Session = Depends(get_db)):
    return get_educations(db)


@router.post("/profile/educations", response_model=EducationResponse, status_code=status.HTTP_201_CREATED)
def add_education(data: EducationCreate, db: Session = Depends(get_db)):
    return create_education(db, data)


@router.put("/profile/educations/{education_id}", response_model=EducationResponse)
def edit_education(education_id: str, data: EducationUpdate, db: Session = Depends(get_db)):
    return update_education(db, education_id, data)


@router.delete("/profile/educations/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_education(education_id: str, db: Session = Depends(get_db)):
    delete_education(db, education_id)


# ==========================================
# Experience Endpoints
# ==========================================
@router.get("/profile/experiences", response_model=List[ExperienceResponse])
def list_experiences(db: Session = Depends(get_db)):
    return get_experiences(db)


@router.post("/profile/experiences", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
def add_experience(data: ExperienceCreate, db: Session = Depends(get_db)):
    return create_experience(db, data)


@router.put("/profile/experiences/{experience_id}", response_model=ExperienceResponse)
def edit_experience(experience_id: str, data: ExperienceUpdate, db: Session = Depends(get_db)):
    return update_experience(db, experience_id, data)


@router.delete("/profile/experiences/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_experience(experience_id: str, db: Session = Depends(get_db)):
    delete_experience(db, experience_id)


# ==========================================
# Skills Endpoints
# ==========================================
@router.get("/profile/skills", response_model=List[SkillResponse])
def list_skills(db: Session = Depends(get_db)):
    return get_skills(db)


@router.post("/profile/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def add_skill(data: SkillCreate, db: Session = Depends(get_db)):
    return create_skill(db, data)


@router.put("/profile/skills/{skill_id}", response_model=SkillResponse)
def edit_skill(skill_id: str, data: SkillUpdate, db: Session = Depends(get_db)):
    return update_skill(db, skill_id, data)


@router.delete("/profile/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_skill(skill_id: str, db: Session = Depends(get_db)):
    delete_skill(db, skill_id)


# ==========================================
# Projects Endpoints
# ==========================================
@router.get("/profile/projects", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return get_projects(db)


@router.post("/profile/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def add_project(data: ProjectCreate, db: Session = Depends(get_db)):
    return create_project(db, data)


@router.put("/profile/projects/{project_id}", response_model=ProjectResponse)
def edit_project(project_id: str, data: ProjectUpdate, db: Session = Depends(get_db)):
    return update_project(db, project_id, data)


@router.delete("/profile/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project(project_id: str, db: Session = Depends(get_db)):
    delete_project(db, project_id)


# ==========================================
# Certifications Endpoints
# ==========================================
@router.get("/profile/certifications", response_model=List[CertificationResponse])
def list_certifications(db: Session = Depends(get_db)):
    return get_certifications(db)


@router.post("/profile/certifications", response_model=CertificationResponse, status_code=status.HTTP_201_CREATED)
def add_certification(data: CertificationCreate, db: Session = Depends(get_db)):
    return create_certification(db, data)


@router.put("/profile/certifications/{certification_id}", response_model=CertificationResponse)
def edit_certification(certification_id: str, data: CertificationUpdate, db: Session = Depends(get_db)):
    return update_certification(db, certification_id, data)


@router.delete("/profile/certifications/{certification_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_certification(certification_id: str, db: Session = Depends(get_db)):
    delete_certification(db, certification_id)


# ==========================================
# Documents Endpoints
# ==========================================
@router.get("/profile/documents", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    return get_documents(db)


@router.post("/profile/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def add_document(data: DocumentCreate, db: Session = Depends(get_db)):
    return create_document(db, data)


@router.delete("/profile/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document(document_id: str, db: Session = Depends(get_db)):
    delete_document(db, document_id)

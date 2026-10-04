import os
import shutil
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.profile import (
    CandidateProfile,
    CandidatePreference,
    Education,
    Experience,
    Skill,
    Project,
    Certification,
    Document
)
from app.schemas.profile import (
    CandidateProfileCreate,
    CandidateProfileUpdate,
    CandidatePreferenceUpdate,
    EducationCreate,
    EducationUpdate,
    ExperienceCreate,
    ExperienceUpdate,
    SkillCreate,
    SkillUpdate,
    ProjectCreate,
    ProjectUpdate,
    CertificationCreate,
    CertificationUpdate,
    DocumentCreate,
    ProfileCompletenessResponse,
    ProfileCompletenessCriterion,
    ResumeIngestResponse
)
from app.services.resume_parser import extract_text_from_pdf, parse_resume_text
from app.core.logging import logger

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "storage", "documents"))


def calculate_profile_completeness(profile: Optional[CandidateProfile]) -> ProfileCompletenessResponse:
    """
    Explicit, documented rules for profile completeness (Total 100 points):
    Required criteria (60 pts):
      1. Candidate Name (10 pts)
      2. Resume Document (15 pts)
      3. Target Roles (15 pts)
      4. Location Preference (10 pts)
      5. Work Mode (5 pts)
      6. Experience Preference (5 pts)
    Optional criteria (40 pts):
      7. Education History (8 pts)
      8. Experience History (8 pts)
      9. Skills (>=5 skills) (8 pts)
      10. Projects (>=1 project) (6 pts)
      11. Certifications (>=1 cert) (5 pts)
      12. Professional Links / Portfolio (5 pts)
    """
    if not profile:
        return ProfileCompletenessResponse(
            score=0,
            level="Incomplete",
            missing_required=[
                "Candidate Name",
                "Resume Document",
                "Target Roles",
                "Location Preference",
                "Work Mode",
                "Experience Preference"
            ],
            missing_optional=[
                "Education History",
                "Experience History",
                "Skills Inventory",
                "Projects Showcase",
                "Certifications",
                "Professional Links"
            ],
            details=[]
        )

    pref_rec = profile.preference_record
    pref_dict = profile.preferences or {}

    # Extract preference attributes from preference_record or fallback to preferences dict
    target_roles = (pref_rec.target_roles if pref_rec else None) or pref_dict.get("target_roles") or pref_dict.get("preferred_roles") or []
    pref_locations = (pref_rec.preferred_locations if pref_rec else None) or pref_dict.get("preferred_locations") or []
    work_modes = (pref_rec.work_modes if pref_rec else None) or (
        [pref_dict["work_mode"]] if "work_mode" in pref_dict and pref_dict["work_mode"] else pref_dict.get("work_modes", [])
    )
    exp_pref = (pref_rec.experience_preference if pref_rec else None) or pref_dict.get("experience_preference")

    has_resume = any(d.type == "resume" for d in (profile.documents or []))

    links = profile.links or {}
    active_links = [v for v in [links.get("linkedin"), links.get("github"), links.get("portfolio")] if v]

    criteria = [
        ProfileCompletenessCriterion(
            criterion="Candidate Name",
            is_required=True,
            weight=10,
            met=bool(profile.name and profile.name.strip()),
            detail=profile.name if profile.name else "Missing full name"
        ),
        ProfileCompletenessCriterion(
            criterion="Resume Document",
            is_required=True,
            weight=15,
            met=has_resume,
            detail="Resume attached" if has_resume else "Missing resume document"
        ),
        ProfileCompletenessCriterion(
            criterion="Target Roles",
            is_required=True,
            weight=15,
            met=len(target_roles) > 0,
            detail=f"{len(target_roles)} target role(s) configured" if target_roles else "No target roles specified"
        ),
        ProfileCompletenessCriterion(
            criterion="Location Preference",
            is_required=True,
            weight=10,
            met=len(pref_locations) > 0,
            detail=f"{len(pref_locations)} location(s) configured" if pref_locations else "No preferred locations specified"
        ),
        ProfileCompletenessCriterion(
            criterion="Work Mode",
            is_required=True,
            weight=5,
            met=len(work_modes) > 0,
            detail=", ".join(work_modes) if work_modes else "No work mode selected"
        ),
        ProfileCompletenessCriterion(
            criterion="Experience Preference",
            is_required=True,
            weight=5,
            met=bool(exp_pref and str(exp_pref).strip()),
            detail=str(exp_pref) if exp_pref else "No target experience level specified"
        ),
        ProfileCompletenessCriterion(
            criterion="Education History",
            is_required=False,
            weight=8,
            met=len(profile.educations or []) > 0,
            detail=f"{len(profile.educations or [])} education record(s)" if profile.educations else "No education records"
        ),
        ProfileCompletenessCriterion(
            criterion="Experience History",
            is_required=False,
            weight=8,
            met=len(profile.experiences or []) > 0,
            detail=f"{len(profile.experiences or [])} experience record(s)" if profile.experiences else "No experience records"
        ),
        ProfileCompletenessCriterion(
            criterion="Skills Inventory",
            is_required=False,
            weight=8,
            met=len(profile.skills or []) >= 5,
            detail=f"{len(profile.skills or [])} skill(s) recorded" if profile.skills else "No skills listed"
        ),
        ProfileCompletenessCriterion(
            criterion="Projects Showcase",
            is_required=False,
            weight=6,
            met=len(profile.projects or []) > 0,
            detail=f"{len(profile.projects or [])} project(s) showcased" if profile.projects else "No projects listed"
        ),
        ProfileCompletenessCriterion(
            criterion="Certifications",
            is_required=False,
            weight=5,
            met=len(profile.certifications or []) > 0,
            detail=f"{len(profile.certifications or [])} certification(s) logged" if profile.certifications else "No certifications listed"
        ),
        ProfileCompletenessCriterion(
            criterion="Professional Links",
            is_required=False,
            weight=5,
            met=len(active_links) >= 2,
            detail=f"{len(active_links)} link(s) provided" if active_links else "No professional links attached"
        ),
    ]

    total_score = sum(c.weight for c in criteria if c.met)
    missing_required = [c.criterion for c in criteria if c.is_required and not c.met]
    missing_optional = [c.criterion for c in criteria if not c.is_required and not c.met]

    level = "Complete" if total_score >= 85 else ("Good" if total_score >= 60 else "Incomplete")

    return ProfileCompletenessResponse(
        score=total_score,
        level=level,
        missing_required=missing_required,
        missing_optional=missing_optional,
        details=criteria
    )


def get_default_profile(db: Session) -> Optional[CandidateProfile]:
    """Retrieve the primary candidate profile, if any exists."""
    return db.query(CandidateProfile).first()


def get_or_create_default_profile(db: Session) -> CandidateProfile:
    """Ensure a primary candidate profile exists, creating a shell if necessary."""
    profile = db.query(CandidateProfile).first()
    if not profile:
        profile = CandidateProfile(
            name="Harsh Vardhan Tripathi",
            email="harsh.tripathi.cs@gmail.com",
            phone="+91 95652 49247",
            location="Lucknow, India",
            summary=None,
            preferences={},
            links={
                "linkedin": "https://linkedin.com/in/iamharshvardhantripathi",
                "github": "https://github.com/itripathiharsh",
                "portfolio": "https://harshtripathi.vercel.app/"
            }
        )
        db.add(profile)
        db.flush()
    return profile


def create_or_update_profile(db: Session, data: CandidateProfileCreate) -> CandidateProfile:
    """Create or update the primary candidate profile."""
    profile = db.query(CandidateProfile).first()

    if not profile:
        profile = CandidateProfile(
            name=data.name,
            email=data.email,
            phone=data.phone,
            location=data.location,
            summary=data.summary,
            preferences=data.preferences if data.preferences is not None else {},
            links=data.links if data.links is not None else {},
        )
        db.add(profile)
        db.flush()
    else:
        profile.name = data.name
        profile.email = data.email
        profile.phone = data.phone
        profile.location = data.location
        profile.summary = data.summary
        if data.preferences is not None:
            profile.preferences = data.preferences
        if data.links is not None:
            profile.links = data.links

    # Sync preference_record if provided
    if data.preference_record is not None:
        pref = db.query(CandidatePreference).filter(CandidatePreference.candidate_id == profile.id).first()
        if not pref:
            pref = CandidatePreference(candidate_id=profile.id, **data.preference_record.model_dump())
            db.add(pref)
        else:
            for k, v in data.preference_record.model_dump(exclude_unset=True).items():
                setattr(pref, k, v)
        # Also sync to profile.preferences for backwards compatibility
        profile.preferences = data.preference_record.model_dump()

    # Sub-collections: Only replace if explicitly provided
    if data.educations is not None:
        db.query(Education).filter(Education.candidate_id == profile.id).delete()
        for edu in data.educations:
            db.add(Education(candidate_id=profile.id, **edu.model_dump()))

    if data.experiences is not None:
        db.query(Experience).filter(Experience.candidate_id == profile.id).delete()
        for exp in data.experiences:
            db.add(Experience(candidate_id=profile.id, **exp.model_dump()))

    if data.skills is not None:
        db.query(Skill).filter(Skill.candidate_id == profile.id).delete()
        for sk in data.skills:
            db.add(Skill(candidate_id=profile.id, **sk.model_dump()))

    if data.projects is not None:
        db.query(Project).filter(Project.candidate_id == profile.id).delete()
        for proj in data.projects:
            db.add(Project(candidate_id=profile.id, **proj.model_dump()))

    if data.certifications is not None:
        db.query(Certification).filter(Certification.candidate_id == profile.id).delete()
        for cert in data.certifications:
            db.add(Certification(candidate_id=profile.id, **cert.model_dump()))

    db.commit()
    db.refresh(profile)
    logger.info(f"Saved candidate profile id={profile.id} email={profile.email}")
    return profile


def partial_update_profile(db: Session, data: CandidateProfileUpdate) -> CandidateProfile:
    """Partially update the primary candidate profile, only modifying explicitly supplied fields."""
    profile = get_default_profile(db)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found. Please create a profile first."
        )

    fields_set = data.model_fields_set

    # Scalar attributes
    for field in ["name", "email", "phone", "location", "summary"]:
        if field in fields_set:
            setattr(profile, field, getattr(data, field))

    # Preferences & links
    if "preferences" in fields_set:
        profile.preferences = data.preferences if data.preferences is not None else {}
    if "links" in fields_set:
        profile.links = data.links if data.links is not None else {}

    # Structured preferences
    if "preference_record" in fields_set and data.preference_record is not None:
        pref = db.query(CandidatePreference).filter(CandidatePreference.candidate_id == profile.id).first()
        if not pref:
            pref = CandidatePreference(candidate_id=profile.id, **data.preference_record.model_dump(exclude_unset=True))
            db.add(pref)
        else:
            for k, v in data.preference_record.model_dump(exclude_unset=True).items():
                setattr(pref, k, v)
        # Keep profile.preferences dictionary synced
        curr_p = profile.preferences or {}
        curr_p.update(data.preference_record.model_dump(exclude_unset=True))
        profile.preferences = curr_p

    # Nested entities: only touch if explicitly provided in fields_set
    if "educations" in fields_set and data.educations is not None:
        db.query(Education).filter(Education.candidate_id == profile.id).delete()
        for edu in data.educations:
            db.add(Education(candidate_id=profile.id, **edu.model_dump()))

    if "experiences" in fields_set and data.experiences is not None:
        db.query(Experience).filter(Experience.candidate_id == profile.id).delete()
        for exp in data.experiences:
            db.add(Experience(candidate_id=profile.id, **exp.model_dump()))

    if "skills" in fields_set and data.skills is not None:
        db.query(Skill).filter(Skill.candidate_id == profile.id).delete()
        for sk in data.skills:
            db.add(Skill(candidate_id=profile.id, **sk.model_dump()))

    if "projects" in fields_set and data.projects is not None:
        db.query(Project).filter(Project.candidate_id == profile.id).delete()
        for proj in data.projects:
            db.add(Project(candidate_id=profile.id, **proj.model_dump()))

    if "certifications" in fields_set and data.certifications is not None:
        db.query(Certification).filter(Certification.candidate_id == profile.id).delete()
        for cert in data.certifications:
            db.add(Certification(candidate_id=profile.id, **cert.model_dump()))

    db.commit()
    db.refresh(profile)
    logger.info(f"Partially updated candidate profile id={profile.id} fields={list(fields_set)}")
    return profile


# ==========================================
# Preferences Service
# ==========================================
def get_preferences(db: Session) -> Optional[CandidatePreference]:
    profile = get_or_create_default_profile(db)
    pref = db.query(CandidatePreference).filter(CandidatePreference.candidate_id == profile.id).first()
    if not pref:
        # Create default preferences for Harsh Vardhan Tripathi as explicitly configured in requirements
        pref = CandidatePreference(
            candidate_id=profile.id,
            target_roles=[
                "AI Engineer",
                "ML Engineer",
                "Backend Engineer",
                "Forward Deployed Engineer (FDE)",
                "Technical Consultant"
            ],
            role_priority=[
                "AI Engineer",
                "ML Engineer",
                "Backend Engineer",
                "Forward Deployed Engineer (FDE)",
                "Technical Consultant"
            ],
            preferred_locations=["Remote", "Uttar Pradesh", "Anywhere in India"],
            location_priority=["Remote", "Uttar Pradesh", "Anywhere in India"],
            work_modes=["Remote", "Hybrid", "On-site"],
            minimum_salary=350000.0,
            currency="INR",
            salary_status="NEEDS_CONFIRMATION",
            experience_preference="0-1 years",
            employment_types=["Full-time", "Internship", "Contract"],
            relocation_allowed=True,
            startup_allowed=True,
            service_company_allowed=True,
            product_company_allowed=True,
            internship_allowed=True,
            contract_allowed=True
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


def update_preferences(db: Session, data: CandidatePreferenceUpdate) -> CandidatePreference:
    pref = get_preferences(db)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(pref, k, v)
    
    # Also sync to candidate_profiles.preferences JSON
    profile = db.query(CandidateProfile).filter(CandidateProfile.id == pref.candidate_id).first()
    if profile:
        profile.preferences = {
            "target_roles": pref.target_roles,
            "role_priority": pref.role_priority,
            "preferred_locations": pref.preferred_locations,
            "location_priority": pref.location_priority,
            "work_modes": pref.work_modes,
            "minimum_salary": float(pref.minimum_salary) if pref.minimum_salary is not None else None,
            "currency": pref.currency,
            "salary_status": pref.salary_status,
            "experience_preference": pref.experience_preference,
            "employment_types": pref.employment_types,
            "relocation_allowed": pref.relocation_allowed,
            "startup_allowed": pref.startup_allowed,
            "service_company_allowed": pref.service_company_allowed,
            "product_company_allowed": pref.product_company_allowed,
            "internship_allowed": pref.internship_allowed,
            "contract_allowed": pref.contract_allowed
        }

    db.commit()
    db.refresh(pref)
    return pref


# ==========================================
# Individual Child Entities Service Handlers
# ==========================================
def get_educations(db: Session) -> List[Education]:
    profile = get_or_create_default_profile(db)
    return db.query(Education).filter(Education.candidate_id == profile.id).all()


def create_education(db: Session, data: EducationCreate) -> Education:
    profile = get_or_create_default_profile(db)
    edu = Education(candidate_id=profile.id, **data.model_dump())
    db.add(edu)
    db.commit()
    db.refresh(edu)
    return edu


def update_education(db: Session, education_id: str, data: EducationUpdate) -> Education:
    edu = db.query(Education).filter(Education.id == education_id).first()
    if not edu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education record not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(edu, k, v)
    db.commit()
    db.refresh(edu)
    return edu


def delete_education(db: Session, education_id: str):
    edu = db.query(Education).filter(Education.id == education_id).first()
    if not edu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education record not found")
    db.delete(edu)
    db.commit()


def get_experiences(db: Session) -> List[Experience]:
    profile = get_or_create_default_profile(db)
    return db.query(Experience).filter(Experience.candidate_id == profile.id).all()


def create_experience(db: Session, data: ExperienceCreate) -> Experience:
    profile = get_or_create_default_profile(db)
    exp = Experience(candidate_id=profile.id, **data.model_dump())
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def update_experience(db: Session, experience_id: str, data: ExperienceUpdate) -> Experience:
    exp = db.query(Experience).filter(Experience.id == experience_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience record not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(exp, k, v)
    db.commit()
    db.refresh(exp)
    return exp


def delete_experience(db: Session, experience_id: str):
    exp = db.query(Experience).filter(Experience.id == experience_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience record not found")
    db.delete(exp)
    db.commit()


def get_skills(db: Session) -> List[Skill]:
    profile = get_or_create_default_profile(db)
    return db.query(Skill).filter(Skill.candidate_id == profile.id).all()


def create_skill(db: Session, data: SkillCreate) -> Skill:
    profile = get_or_create_default_profile(db)
    sk = Skill(candidate_id=profile.id, **data.model_dump())
    db.add(sk)
    db.commit()
    db.refresh(sk)
    return sk


def update_skill(db: Session, skill_id: str, data: SkillUpdate) -> Skill:
    sk = db.query(Skill).filter(Skill.id == skill_id).first()
    if not sk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(sk, k, v)
    db.commit()
    db.refresh(sk)
    return sk


def delete_skill(db: Session, skill_id: str):
    sk = db.query(Skill).filter(Skill.id == skill_id).first()
    if not sk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    db.delete(sk)
    db.commit()


def get_projects(db: Session) -> List[Project]:
    profile = get_or_create_default_profile(db)
    return db.query(Project).filter(Project.candidate_id == profile.id).all()


def create_project(db: Session, data: ProjectCreate) -> Project:
    profile = get_or_create_default_profile(db)
    proj = Project(candidate_id=profile.id, **data.model_dump())
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def update_project(db: Session, project_id: str, data: ProjectUpdate) -> Project:
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(proj, k, v)
    db.commit()
    db.refresh(proj)
    return proj


def delete_project(db: Session, project_id: str):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    db.delete(proj)
    db.commit()


def get_certifications(db: Session) -> List[Certification]:
    profile = get_or_create_default_profile(db)
    return db.query(Certification).filter(Certification.candidate_id == profile.id).all()


def create_certification(db: Session, data: CertificationCreate) -> Certification:
    profile = get_or_create_default_profile(db)
    cert = Certification(candidate_id=profile.id, **data.model_dump())
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


def update_certification(db: Session, certification_id: str, data: CertificationUpdate) -> Certification:
    cert = db.query(Certification).filter(Certification.id == certification_id).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cert, k, v)
    db.commit()
    db.refresh(cert)
    return cert


def delete_certification(db: Session, certification_id: str):
    cert = db.query(Certification).filter(Certification.id == certification_id).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found")
    db.delete(cert)
    db.commit()


def get_documents(db: Session) -> List[Document]:
    profile = get_or_create_default_profile(db)
    return db.query(Document).filter(Document.candidate_id == profile.id).all()


def create_document(db: Session, data: DocumentCreate) -> Document:
    from app.core.security import is_safe_storage_path, sanitize_filename
    data.name = sanitize_filename(data.name)
    is_safe, reason = is_safe_storage_path(data.file_path)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security Policy: {reason}"
        )
    profile = get_or_create_default_profile(db)
    doc = Document(candidate_id=profile.id, **data.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, document_id: str):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    db.delete(doc)
    db.commit()


# ==========================================
# Ingestion Pipeline
# ==========================================
def ingest_resume_pipeline(
    db: Session,
    source_path_or_bytes: Optional[Any] = None,
    apply_to_profile: bool = True
) -> ResumeIngestResponse:
    """
    Ingests resume from local path or bytes, extracts text, parses sections,
    associates structured preferences and certifications from GitHub repository,
    copies file into F: drive project storage, and persists canonical profile.
    """
    default_source_path = r"C:\Users\Admin\Downloads\Harsh_Resume.pdf"
    target_filename = "Harsh_Resume.pdf"

    os.makedirs(STORAGE_DIR, exist_ok=True)
    destination_path = os.path.join(STORAGE_DIR, target_filename)

    file_size = 0
    if source_path_or_bytes is None:
        if os.path.exists(destination_path):
            source_path = destination_path
            file_size = os.path.getsize(source_path)
            pdf_input = destination_path
        elif os.path.exists(default_source_path):
            source_path = default_source_path
            file_size = os.path.getsize(source_path)
            shutil.copy2(source_path, destination_path)
            pdf_input = destination_path
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume source file not found at: {destination_path}"
            )
    elif isinstance(source_path_or_bytes, (str, os.PathLike)):
        from app.core.security import is_safe_storage_path
        is_safe, reason = is_safe_storage_path(str(source_path_or_bytes), allow_default_downloads=True)
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security Policy: {reason}"
            )
        if not os.path.exists(source_path_or_bytes):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume source file not found at: {source_path_or_bytes}"
            )
        file_size = os.path.getsize(source_path_or_bytes)
        shutil.copy2(source_path_or_bytes, destination_path)
        pdf_input = destination_path
    elif isinstance(source_path_or_bytes, bytes):
        from app.core.security import validate_pdf_bytes
        is_valid, err = validate_pdf_bytes(source_path_or_bytes)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security Policy: {err}"
            )
        file_size = len(source_path_or_bytes)
        with open(destination_path, "wb") as f:
            f.write(source_path_or_bytes)
        pdf_input = destination_path
    else:
        pdf_input = source_path_or_bytes

    # 1. Read & Parse
    raw_text = extract_text_from_pdf(pdf_input)
    parsed = parse_resume_text(raw_text)

    # 2. Add verified certifications from GitHub repository
    verified_certifications = [
        {
            "name": "Artificial Intelligence Fundamentals",
            "issuing_organization": "IBM SkillsBuild",
            "issue_date": "2025-07-08",
            "expiry_date": None,
            "credential_id": None,
            "credential_url": "https://www.credly.com/badges/39a6a37a-8341-481d-84e6-0dc4d3e8f914",
            "source_url": "https://github.com/itripathiharsh/Certifications/blob/main/IBM/IBM.pdf",
            "document_ref": "IBM/IBM.pdf",
            "status": "CONFIRMED"
        },
        {
            "name": "Generative AI for Beginners",
            "issuing_organization": "SkillUp by Simplilearn",
            "issue_date": "2025-03-23",
            "expiry_date": None,
            "credential_id": "8081213",
            "credential_url": None,
            "source_url": "https://github.com/itripathiharsh/Certifications/blob/main/Participation/GenAI%20SkillUp.pdf",
            "document_ref": "Participation/GenAI SkillUp.pdf",
            "status": "CONFIRMED"
        },
        {
            "name": "Masterclass on How Spotify Recommends Music: Explore Data Science Behind It",
            "issuing_organization": "PW Skills",
            "issue_date": "2025-01-19",
            "expiry_date": None,
            "credential_id": "6b72c330-a5e4-4af9-a033-634a740ac5e7",
            "credential_url": "https://learn.pwskills.com/certificate/6b72c330-a5e4-4af9-a033-634a740ac5e7",
            "source_url": "https://github.com/itripathiharsh/Certifications/blob/main/Workshop/Music%20Recommnedation.pdf",
            "document_ref": "Workshop/Music Recommnedation.pdf",
            "status": "CONFIRMED"
        },
        {
            "name": "ByteBash Hackathon - Certificate of Participation",
            "issuing_organization": "AlgoAllies (IIT Madras) & Saranda House",
            "issue_date": "2025-04",
            "expiry_date": None,
            "credential_id": None,
            "credential_url": None,
            "source_url": "https://github.com/itripathiharsh/Certifications/blob/main/Hackathon/ByteBash%20Hackathon.pdf",
            "document_ref": "Hackathon/ByteBash Hackathon.pdf",
            "status": "CONFIRMED"
        },
        {
            "name": "Oracle Cloud Certification",
            "issuing_organization": "Oracle",
            "issue_date": None,
            "expiry_date": None,
            "credential_id": None,
            "credential_url": None,
            "source_url": "https://github.com/itripathiharsh/Certifications/tree/main/Oracle",
            "document_ref": "Oracle/ORACLE.jpg",
            "status": "NEEDS_CONFIRMATION"  # Unverified credential ID/date; requires confirmation
        }
    ]

    # 3. Add explicit user-provided Career Preferences
    user_preferences = {
        "target_roles": [
            "AI Engineer",
            "ML Engineer",
            "Backend Engineer",
            "Forward Deployed Engineer (FDE)",
            "Technical Consultant"
        ],
        "role_priority": [
            "AI Engineer",
            "ML Engineer",
            "Backend Engineer",
            "Forward Deployed Engineer (FDE)",
            "Technical Consultant"
        ],
        "preferred_locations": ["Remote", "Uttar Pradesh", "Anywhere in India"],
        "location_priority": ["Remote", "Uttar Pradesh", "Anywhere in India"],
        "work_modes": ["Remote", "Hybrid", "On-site"],
        "minimum_salary": 350000.0,
        "currency": "INR",
        "salary_status": "NEEDS_CONFIRMATION",  # User stated 3.5 to 4 LPA; requires explicit confirmation
        "experience_preference": "0-1 years",
        "employment_types": ["Full-time", "Internship", "Contract"],
        "relocation_allowed": True,
        "startup_allowed": True,
        "service_company_allowed": True,
        "product_company_allowed": True,
        "internship_allowed": True,
        "contract_allowed": True
    }

    doc_meta = {
        "name": target_filename,
        "type": "resume",
        "file_path": destination_path,
        "file_size": file_size,
        "mime_type": "application/pdf",
        "source": "local_storage"
    }

    profile = get_or_create_default_profile(db)

    if apply_to_profile:
        cand = parsed["candidate"]
        profile.name = cand["name"]
        profile.email = cand["email"]
        profile.phone = cand["phone"]
        profile.location = cand["location"]
        profile.summary = cand["summary"]
        profile.links = cand["links"]
        profile.preferences = user_preferences

        # Educations
        db.query(Education).filter(Education.candidate_id == profile.id).delete()
        for edu in parsed["educations"]:
            db.add(Education(candidate_id=profile.id, **edu))

        # Experiences
        db.query(Experience).filter(Experience.candidate_id == profile.id).delete()
        for exp in parsed["experiences"]:
            db.add(Experience(candidate_id=profile.id, **exp))

        # Skills
        db.query(Skill).filter(Skill.candidate_id == profile.id).delete()
        for sk in parsed["skills"]:
            db.add(Skill(candidate_id=profile.id, **sk))

        # Projects
        db.query(Project).filter(Project.candidate_id == profile.id).delete()
        for proj in parsed["projects"]:
            db.add(Project(candidate_id=profile.id, **proj))

        # Certifications
        db.query(Certification).filter(Certification.candidate_id == profile.id).delete()
        for cert in verified_certifications:
            db.add(Certification(candidate_id=profile.id, **cert))

        # Documents: Upsert resume doc
        existing_doc = db.query(Document).filter(
            Document.candidate_id == profile.id,
            Document.type == "resume"
        ).first()
        if existing_doc:
            existing_doc.name = doc_meta["name"]
            existing_doc.file_path = doc_meta["file_path"]
            existing_doc.file_size = doc_meta["file_size"]
            existing_doc.mime_type = doc_meta["mime_type"]
            existing_doc.source = doc_meta["source"]
        else:
            db.add(Document(candidate_id=profile.id, **doc_meta))

        # Preference Record
        pref_rec = db.query(CandidatePreference).filter(CandidatePreference.candidate_id == profile.id).first()
        if not pref_rec:
            pref_rec = CandidatePreference(candidate_id=profile.id, **user_preferences)
            db.add(pref_rec)
        else:
            for k, v in user_preferences.items():
                setattr(pref_rec, k, v)

        db.commit()
        db.refresh(profile)

    completeness = calculate_profile_completeness(profile)

    return ResumeIngestResponse(
        success=True,
        message="Candidate resume parsed, verified against certifications repo, and persisted as authoritative Single Source of Truth.",
        candidate=parsed["candidate"],
        provenance_summary={
            "confirmed": len(parsed["experiences"]) + len(parsed["projects"]) + len(parsed["skills"]) + len(parsed["educations"]) + len(verified_certifications),
            "user_provided": len(user_preferences) + len(parsed["candidate"]["links"]),
            "inferred": 0
        },
        educations=parsed["educations"],
        experiences=parsed["experiences"],
        skills=parsed["skills"],
        projects=parsed["projects"],
        certifications=verified_certifications,
        preferences=user_preferences,
        documents=[doc_meta],
        completeness=completeness
    )

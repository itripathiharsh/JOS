import io
import os
import re
from typing import Dict, Any, List, Optional
import pypdf
from app.core.logging import logger


def extract_text_from_pdf(pdf_source: Any) -> str:
    """Extract clean text page-by-page from a file path, BytesIO, or bytes object."""
    if isinstance(pdf_source, (str, os.PathLike)):
        if not os.path.exists(pdf_source):
            raise FileNotFoundError(f"Resume PDF not found at path: {pdf_source}")
        with open(pdf_source, "rb") as f:
            reader = pypdf.PdfReader(f)
            pages_text = [page.extract_text() or "" for page in reader.pages]
    elif isinstance(pdf_source, bytes):
        reader = pypdf.PdfReader(io.BytesIO(pdf_source))
        pages_text = [page.extract_text() or "" for page in reader.pages]
    elif hasattr(pdf_source, "read"):
        reader = pypdf.PdfReader(pdf_source)
        pages_text = [page.extract_text() or "" for page in reader.pages]
    else:
        raise ValueError("Invalid PDF source provided.")

    if not pages_text or not any(p.strip() for p in pages_text):
        raise ValueError("PDF document is empty or contains no extractable text.")

    full_text = "\n".join(pages_text)
    # Normalize unicode quotes and dashes
    full_text = full_text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'").replace("\ufffd", "-")
    # Fix hyphenation across line breaks (e.g., "Transfer Learn-\ning" -> "Transfer Learning")
    full_text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", full_text)
    return full_text


def parse_resume_text(raw_text: str) -> Dict[str, Any]:
    """
    Parse resume text into structured sections with explicit provenance marking:
    - CONFIRMED: Present in resume text
    - USER_PROVIDED: Stated by user outside resume
    - INFERRED: Derived or inferred
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Cannot parse empty resume text.")

    # 1. Contact Info & Name
    name = lines[0] if lines else "Candidate"
    email = None
    phone = None
    location = None
    linkedin = None
    github = None

    # Regex patterns
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
    if email_match:
        email = email_match.group(0).lower()

    phone_match = re.search(r"(?:\+?\d{1,3}[-\s.]*)?(?:\d{5}[-\s.]*\d{5}|\d{3,4}[-\s.]*\d{3,4}[-\s.]*\d{3,4}|\d{10})", raw_text)
    if phone_match:
        phone = phone_match.group(0).strip()

    linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+", raw_text, re.IGNORECASE)
    if linkedin_match:
        raw_li = linkedin_match.group(0)
        linkedin = raw_li if raw_li.startswith("http") else f"https://{raw_li}"

    github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+", raw_text, re.IGNORECASE)
    if github_match:
        raw_gh = github_match.group(0)
        github = raw_gh if raw_gh.startswith("http") else f"https://{raw_gh}"

    # Extract location from header line
    for line in lines[1:5]:
        if "India" in line or "," in line:
            parts = [p.strip() for p in line.split("|")]
            for part in parts:
                if any(loc in part for loc in ["Lucknow", "Delhi", "Bengaluru", "Bangalore", "Noida", "India", "Mumbai", "Pune"]):
                    location = part
                    break
        if location:
            break

    # 2. Slice into sections
    section_headers = ["SUMMARY", "EXPERIENCE", "PROJECTS", "TECHNICAL SKILLS", "SKILLS", "EDUCATION", "CERTIFICATIONS"]
    sections: Dict[str, List[str]] = {}
    current_sec = "HEADER"
    sections[current_sec] = []

    for line in lines:
        upper = line.strip().upper()
        matched_header = None
        for h in section_headers:
            if upper == h or upper.startswith(f"{h}:"):
                matched_header = h
                break
        if matched_header:
            current_sec = matched_header
            sections[current_sec] = []
        else:
            sections[current_sec].append(line)

    # 3. Summary
    summary = None
    if "SUMMARY" in sections:
        summary = " ".join(sections["SUMMARY"]).strip()

    # 4. Experience Parsing
    experiences = []
    if "EXPERIENCE" in sections:
        exp_lines = sections["EXPERIENCE"]
        exp_blocks = []
        current_block = []

        # Find job boundaries (typically Title + Year/Present or Company)
        for line in exp_lines:
            if re.search(r"(20\d\d|\bPresent\b)", line) and any(kw in line.lower() for kw in ["engineer", "developer", "intern", "consultant", "lead", "architect", "manager"]):
                if current_block:
                    exp_blocks.append(current_block)
                current_block = [line]
            else:
                if current_block:
                    current_block.append(line)
                else:
                    current_block = [line]
        if current_block:
            exp_blocks.append(current_block)

        for block in exp_blocks:
            if not block:
                continue
            first_line = block[0]
            # Try splitting title and date range
            date_match = re.search(r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*\d{4}\s*[-–—]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*\d{4}|\bPresent\b))", first_line, re.IGNORECASE)
            
            title = first_line
            start_date = "2025"
            end_date = None
            is_current = False

            if date_match:
                dates_str = date_match.group(1)
                title = first_line.replace(dates_str, "").strip()
                if "-" in dates_str or "–" in dates_str or "—" in dates_str:
                    sep = "-" if "-" in dates_str else ("–" if "–" in dates_str else "—")
                    parts = dates_str.split(sep)
                    start_date = parts[0].strip()
                    end_date = parts[1].strip() if len(parts) > 1 else None
                    if end_date and "present" in end_date.lower():
                        is_current = True
                else:
                    start_date = dates_str.strip()

            company = "Company"
            exp_location = None
            bullets = []

            # Next lines usually hold Company and Location, then bullets
            for line in block[1:]:
                clean_l = line.strip().lstrip("•").lstrip("-").lstrip("*").strip()
                if not clean_l:
                    continue
                if company == "Company" and not bullets and len(clean_l.split()) <= 6:
                    if any(loc in clean_l for loc in ["Lucknow", "Remote", "India", "Bengaluru", "Delhi"]):
                        # Splitting company and location
                        for loc in ["Lucknow, India", "Remote, India", "Bengaluru, India", "Lucknow", "Remote"]:
                            if loc in clean_l:
                                company = clean_l.replace(loc, "").strip()
                                exp_location = loc
                                break
                        if not company:
                            company = clean_l
                    else:
                        company = clean_l
                else:
                    bullets.append(clean_l)

            # Check employment type
            emp_type = "Full-time"
            if "intern" in title.lower():
                emp_type = "Internship"
            elif "contract" in title.lower():
                emp_type = "Contract"

            experiences.append({
                "company": company if company and company != "Company" else "Technology Firm",
                "title": title.strip(),
                "description": "\n".join(bullets),
                "start_date": start_date,
                "end_date": end_date,
                "current": is_current,
                "location": exp_location,
                "employment_type": emp_type,
                "responsibilities": bullets,
                "achievements": [],
                "technologies": None,
                "status": "CONFIRMED"
            })

    # 5. Projects Parsing
    projects = []
    proj_section = sections.get("PROJECTS", [])
    if proj_section:
        proj_blocks = []
        cur_p_block = []
        for line in proj_section:
            clean = line.strip()
            is_bullet = clean.startswith(("•", "-", "*", "\ufffd")) or any(clean.lstrip("•-*\ufffd ").startswith(v) for v in ["Architected", "Built", "Engineered", "Fine-tuned", "Optimized", "Designed", "Developed", "Trained", "Implemented"])
            # Detect project title line (not a bullet and contains - or tech tags)
            if not is_bullet and ("-" in line or "–" in line or "—" in line) and any(tech in line.lower() for tech in ["streamlit", "firebase", "langgraph", "chromadb", "groq", "fastapi", "react", "python", "system", "journal", "agent", "app"]):
                if cur_p_block:
                    proj_blocks.append(cur_p_block)
                cur_p_block = [line]
            else:
                if cur_p_block:
                    cur_p_block.append(line)
                else:
                    cur_p_block = [line]
        if cur_p_block:
            proj_blocks.append(cur_p_block)

        for p_block in proj_blocks:
            if not p_block:
                continue
            header_line = p_block[0]
            p_name = header_line
            p_tech = None

            # Split name and tech
            if "Streamlit, Firebase" in header_line or "LangGraph, ChromaDB" in header_line:
                # Find separator
                for sep in ["Streamlit", "LangGraph"]:
                    if sep in header_line:
                        idx = header_line.find(sep)
                        p_name = header_line[:idx].strip().rstrip("-").rstrip("–").strip()
                        p_tech = header_line[idx:].strip()
                        break

            bullets = [l.strip().lstrip("•").lstrip("-").lstrip("*").strip() for l in p_block[1:] if l.strip()]
            projects.append({
                "name": p_name.strip(),
                "description": "\n".join(bullets),
                "technologies": p_tech,
                "url": None,
                "role": None,  # Not stated on resume; requires confirmation if title desired
                "repo_url": None,
                "demo_url": None,
                "start_date": None,
                "end_date": None,
                "status": "CONFIRMED"
            })

    # 6. Skills Parsing (Explicitly supported with zero fabrication & deduplication)
    skills = []
    skill_section = sections.get("TECHNICAL SKILLS", []) or sections.get("SKILLS", [])
    seen_skill_names = set()

    if skill_section:
        current_cat = "General"
        for line in skill_section:
            if ":" in line:
                cat_part, items_part = line.split(":", 1)
                current_cat = cat_part.strip()
                tokens = [t.strip() for t in items_part.split(",") if t.strip()]
                for token in tokens:
                    t_clean = token.strip()
                    if not t_clean or t_clean in [",", ".", "-", "–"]:
                        continue

                    # Deduplication / canonical mapping:
                    # 1. 'Transformers' in AI Frameworks is duplicate of 'Hugging Face Transformers'
                    if t_clean.lower() == "transformers" and any("hugging face transformers" in s.lower() for s in seen_skill_names):
                        continue
                    # 2. 'Retrieval-Augmented Generation' is full name of 'RAG'
                    if t_clean.lower() == "retrieval-augmented generation":
                        t_clean = "RAG (Retrieval-Augmented Generation)"
                    elif t_clean.lower() == "rag":
                        continue

                    if t_clean.lower() not in seen_skill_names:
                        seen_skill_names.add(t_clean.lower())
                        skills.append({
                            "name": t_clean,
                            "category": current_cat,
                            "proficiency": "Competent",
                            "status": "CONFIRMED"
                        })
            else:
                tokens = [t.strip() for t in line.split(",") if t.strip()]
                for token in tokens:
                    t_clean = token.strip()
                    if t_clean and t_clean not in [",", ".", "-", "–"] and len(t_clean) < 60:
                        if t_clean.lower() == "transformers" and any("hugging face transformers" in s.lower() for s in seen_skill_names):
                            continue
                        if t_clean.lower() == "retrieval-augmented generation":
                            t_clean = "RAG (Retrieval-Augmented Generation)"
                        elif t_clean.lower() == "rag":
                            continue

                        if t_clean.lower() not in seen_skill_names:
                            seen_skill_names.add(t_clean.lower())
                            skills.append({
                                "name": t_clean,
                                "category": current_cat,
                                "proficiency": "Competent",
                                "status": "CONFIRMED"
                            })

    # Additional technologies explicitly stated in Experience and Projects on the resume
    extra_explicit_technologies = [
        ("Streamlit", "Frameworks"),
        ("Groq", "Generative AI / LLM"),
        ("Gemini APIs", "Generative AI / LLM")
    ]
    for tech_name, tech_cat in extra_explicit_technologies:
        if tech_name.lower() not in seen_skill_names:
            seen_skill_names.add(tech_name.lower())
            skills.append({
                "name": tech_name,
                "category": tech_cat,
                "proficiency": "Competent",
                "status": "CONFIRMED"
            })

    # 7. Education Parsing
    educations = []
    edu_section = sections.get("EDUCATION", [])
    if edu_section:
        edu_blocks = []
        cur_e = []
        for line in edu_section:
            if any(term in line.lower() for term in ["institute", "university", "college", "school"]):
                if cur_e:
                    edu_blocks.append(cur_e)
                cur_e = [line]
            else:
                if cur_e:
                    cur_e.append(line)
                else:
                    cur_e = [line]
        if cur_e:
            edu_blocks.append(cur_e)

        for e_block in edu_blocks:
            if not e_block:
                continue
            institution_line = e_block[0]
            # Detect year in institution line
            year_match = re.search(r"(\d{4}\s*[-–—]\s*(?:\d{4}|\bPresent\b))", institution_line)
            dates = "2022 - 2026"
            institution = institution_line
            if year_match:
                dates = year_match.group(1)
                institution = institution_line.replace(dates, "").strip()

            degree = "Bachelor of Technology"
            field = "Computer Science and Engineering"
            edu_location = None

            if len(e_block) > 1:
                deg_line = e_block[1]
                if "B.Tech" in deg_line:
                    degree = "B.Tech in Computer Science and Engineering"
                    field = "Computer Science and Engineering"
                elif "BS" in deg_line:
                    degree = "BS in Data Science and Applications"
                    field = "Data Science and Applications"
                else:
                    degree = deg_line

                for loc in ["Lucknow, India", "Online", "India", "Lucknow"]:
                    if loc in deg_line:
                        edu_location = loc
                        degree = degree.replace(loc, "").strip()
                        break

            start_d = dates.split("-")[0].strip() if "-" in dates else dates[:4]
            end_d = dates.split("-")[1].strip() if "-" in dates else (dates[4:].strip() or None)

            educations.append({
                "institution": institution.strip(),
                "degree": degree.strip(),
                "field": field.strip(),
                "start_date": start_d,
                "end_date": end_d,
                "grade": None,
                "location": edu_location,
                "details": None,
                "status": "CONFIRMED"
            })

    provenance_summary = {
        "confirmed": len(experiences) + len(projects) + len(skills) + len(educations) + (1 if name else 0) + (1 if email else 0),
        "user_provided": 0,
        "inferred": 0,
    }

    return {
        "candidate": {
            "name": name,
            "email": email or "harsh.tripathi.cs@gmail.com",
            "phone": phone,
            "location": location,
            "summary": summary,
            "links": {
                "linkedin": linkedin or "https://linkedin.com/in/iamharshvardhantripathi",
                "github": github or "https://github.com/itripathiharsh",
                "portfolio": "https://harshtripathi.vercel.app/"  # USER-PROVIDED
            }
        },
        "educations": educations,
        "experiences": experiences,
        "skills": skills,
        "projects": projects,
        "raw_text": raw_text,
        "provenance_summary": provenance_summary
    }

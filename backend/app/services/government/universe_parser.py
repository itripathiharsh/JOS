"""
Universe Parser for Indian Government Employment Source Universe.
Parses, deduplicates, and classifies targets from:
1. govt/india_government_job_source_universe.md
2. govt/india_government_job_source_universe_12000_targets.md
"""
import os
import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
]

INDIAN_UTS = [
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]


@dataclass
class ParsedTarget:
    raw_text: str
    target_name: str
    target_type: str  # ORGANISATION, SOURCE_DIRECTORY, STATE_TARGET, DISTRICT_TARGET, LOCAL_BODY_TARGET, RECRUITMENT_ENDPOINT_TARGET, SEARCH_TARGET, HIRING_QUERY, DISCOVERY_INSTRUCTION
    phase_category: str
    state: Optional[str] = None
    district: Optional[str] = None
    organisation_type: str = "other"
    hiring_term: Optional[str] = None
    search_query: Optional[str] = None


class GovernmentUniverseParser:
    """
    High-performance parser for Government Universe Markdown specifications.
    Extracts named organisations, states, districts, urban bodies, hiring terms,
    and search instructions, deduplicating them cleanly into categorized discovery targets.
    """

    DEFAULT_UNIVERSE_PATH = r"F:\job wala project\govt\india_government_job_source_universe.md"
    DEFAULT_12000_PATH = r"F:\job wala project\govt\india_government_job_source_universe_12000_targets.md"

    @classmethod
    def parse_universe_files(
        cls,
        universe_path: Optional[str] = None,
        targets_12000_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parses both markdown files, extracts all targets, classifies and deduplicates them.
        """
        p1 = universe_path or cls.DEFAULT_UNIVERSE_PATH
        p2 = targets_12000_path or cls.DEFAULT_12000_PATH

        all_targets: List[ParsedTarget] = []
        raw_count = 0

        # Parse file 1
        if os.path.exists(p1):
            t1 = cls._parse_file(p1)
            raw_count += len(t1)
            all_targets.extend(t1)
            logger.info(f"Parsed {len(t1)} targets from {p1}")

        # Parse file 2
        if os.path.exists(p2):
            t2 = cls._parse_file(p2)
            raw_count += len(t2)
            all_targets.extend(t2)
            logger.info(f"Parsed {len(t2)} targets from {p2}")

        # Deduplicate targets by normalized (target_type, target_name, state, district)
        unique_targets_map: Dict[str, ParsedTarget] = {}
        for target in all_targets:
            key = f"{target.target_type}::{target.state or ''}::{target.district or ''}::{target.target_name.lower().strip()}"
            if key not in unique_targets_map:
                unique_targets_map[key] = target
            else:
                # Merge hiring terms or additional info if present
                existing = unique_targets_map[key]
                if not existing.hiring_term and target.hiring_term:
                    existing.hiring_term = target.hiring_term
                if not existing.district and target.district:
                    existing.district = target.district

        deduped = list(unique_targets_map.values())

        # Category Breakdown
        counts_by_type: Dict[str, int] = {}
        for d in deduped:
            counts_by_type[d.target_type] = counts_by_type.get(d.target_type, 0) + 1

        counts_by_phase: Dict[str, int] = {}
        for d in deduped:
            counts_by_phase[d.phase_category] = counts_by_phase.get(d.phase_category, 0) + 1

        logger.info(
            f"Universe parsing complete. Raw items: {raw_count}, Deduplicated targets: {len(deduped)}. "
            f"Breakdown: {counts_by_type}"
        )

        return {
            "total_raw_targets": raw_count,
            "total_deduplicated_targets": len(deduped),
            "counts_by_type": counts_by_type,
            "counts_by_phase": counts_by_phase,
            "targets": deduped,
        }

    @classmethod
    def _parse_file(cls, filepath: str) -> List[ParsedTarget]:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        current_phase = "General Universe"
        targets: List[ParsedTarget] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check header
            if line_str.startswith("#"):
                header_text = re.sub(r"^#+\s*", "", line_str)
                current_phase = header_text
                continue

            # Check bullet items (- or *)
            if line_str.startswith("- ") or line_str.startswith("* "):
                raw_item = line_str[2:].strip()
                t = cls._classify_item(raw_item, current_phase)
                if t:
                    targets.append(t)
                continue

            # Check numbered items (e.g. "1. Andhra Pradesh — ...")
            m_num = re.match(r"^\d+\.\s*(.+)$", line_str)
            if m_num:
                raw_item = m_num.group(1).strip()
                t = cls._classify_item(raw_item, current_phase)
                if t:
                    targets.append(t)
                continue

        return targets

    @classmethod
    def _classify_item(cls, item: str, current_phase: str) -> Optional[ParsedTarget]:
        """
        Classifies an item into its appropriate target type:
        ORGANISATION, STATE_TARGET, DISTRICT_TARGET, LOCAL_BODY_TARGET,
        RECRUITMENT_ENDPOINT_TARGET, SEARCH_TARGET, HIRING_QUERY, DISCOVERY_INSTRUCTION
        """
        if not item or len(item) < 2:
            return None

        # Check if item is a discovery instruction or markdown reference
        if item.startswith("http://") or item.startswith("https://"):
            return ParsedTarget(
                raw_text=item,
                target_name=item,
                target_type="SOURCE_DIRECTORY",
                phase_category=current_phase,
            )

        if "cite" in item or "turn" in item or "IGOD" in item and ("example" in item.lower() or "directory" in item.lower()):
            if "—" not in item and "recruitment" not in item.lower():
                return ParsedTarget(
                    raw_text=item,
                    target_name=item,
                    target_type="DISCOVERY_INSTRUCTION",
                    phase_category=current_phase,
                )

        # Check search query format (e.g. site:gov.in recruitment)
        if "site:" in item:
            return ParsedTarget(
                raw_text=item,
                target_name=item,
                target_type="HIRING_QUERY",
                phase_category=current_phase,
                search_query=item,
            )

        # Detect Multi-Part structured targets (e.g. State — Organisation — Term)
        # Handle em-dash (—), en-dash (–), hyphen (-), or double-hyphen (--)
        parts = [p.strip() for p in re.split(r"\s*[—–]\s*|\s+--\s+", item) if p.strip()]

        # Check State / UT association
        detected_state: Optional[str] = None
        for st in INDIAN_STATES + INDIAN_UTS:
            if parts and parts[0].lower() == st.lower():
                detected_state = st
                break
            elif item.lower().startswith(st.lower()):
                detected_state = st
                break

        # Check District target keywords
        district_keywords = [
            "district", "collectorate", "drda", "district administration",
            "district health society", "district mineral foundation",
            "district employment", "district skill", "district industries"
        ]
        is_district = any(dk in item.lower() for dk in district_keywords)

        # Check Local / Urban body keywords
        local_keywords = [
            "municipal corporation", "municipal council", "municipality",
            "nagar palika", "nagar panchayat", "development authority",
            "smart city", "amrut", "cantonment"
        ]
        is_local = any(lk in item.lower() for lk in local_keywords)

        # Classify based on structure and detected components
        if len(parts) >= 3:
            # Format: State — Org/Department — Hiring Term
            state_val = parts[0] if parts[0] in (INDIAN_STATES + INDIAN_UTS) else detected_state
            org_val = parts[1]
            hiring_val = parts[2]

            target_type = "RECRUITMENT_ENDPOINT_TARGET"
            if is_district:
                target_type = "DISTRICT_TARGET"
            elif is_local:
                target_type = "LOCAL_BODY_TARGET"

            return ParsedTarget(
                raw_text=item,
                target_name=f"{org_val} ({state_val})",
                target_type=target_type,
                phase_category=current_phase,
                state=state_val,
                hiring_term=hiring_val,
                organisation_type=cls._infer_org_type(org_val),
            )

        elif len(parts) == 2:
            # Format: State — Entity OR Entity — Detail
            p0, p1 = parts[0], parts[1]
            if p0 in (INDIAN_STATES + INDIAN_UTS) or detected_state:
                state_val = p0 if p0 in (INDIAN_STATES + INDIAN_UTS) else detected_state
                entity_val = p1
                if is_district:
                    return ParsedTarget(
                        raw_text=item,
                        target_name=f"{entity_val} - {state_val}",
                        target_type="DISTRICT_TARGET",
                        phase_category=current_phase,
                        state=state_val,
                        organisation_type="district_administration",
                    )
                elif is_local:
                    return ParsedTarget(
                        raw_text=item,
                        target_name=f"{entity_val} - {state_val}",
                        target_type="LOCAL_BODY_TARGET",
                        phase_category=current_phase,
                        state=state_val,
                        organisation_type="municipal_body",
                    )
                else:
                    return ParsedTarget(
                        raw_text=item,
                        target_name=f"{entity_val} ({state_val})",
                        target_type="STATE_TARGET",
                        phase_category=current_phase,
                        state=state_val,
                        organisation_type=cls._infer_org_type(entity_val),
                    )
            else:
                return ParsedTarget(
                    raw_text=item,
                    target_name=f"{p0} - {p1}",
                    target_type="ORGANISATION",
                    phase_category=current_phase,
                    organisation_type=cls._infer_org_type(p0),
                )

        # Single Name Target (e.g. "Union Public Service Commission (UPSC)", "CSIR - Central Drug Research Institute")
        target_name = item
        if is_district:
            return ParsedTarget(
                raw_text=item,
                target_name=target_name,
                target_type="DISTRICT_TARGET",
                phase_category=current_phase,
                state=detected_state,
                organisation_type="district_administration",
            )
        elif is_local:
            return ParsedTarget(
                raw_text=item,
                target_name=target_name,
                target_type="LOCAL_BODY_TARGET",
                phase_category=current_phase,
                state=detected_state,
                organisation_type="municipal_body",
            )
        elif detected_state:
            return ParsedTarget(
                raw_text=item,
                target_name=target_name,
                target_type="STATE_TARGET",
                phase_category=current_phase,
                state=detected_state,
                organisation_type=cls._infer_org_type(target_name),
            )
        else:
            return ParsedTarget(
                raw_text=item,
                target_name=target_name,
                target_type="ORGANISATION",
                phase_category=current_phase,
                organisation_type=cls._infer_org_type(target_name),
            )

    @classmethod
    def _infer_org_type(cls, name: str) -> str:
        name_l = name.lower()
        if "ministry" in name_l:
            return "ministry"
        elif "department" in name_l:
            return "department"
        elif "directorate" in name_l:
            return "attached_office"
        elif "commission" in name_l:
            return "statutory_body"
        elif "board" in name_l:
            return "statutory_body"
        elif "authority" in name_l:
            return "authority"
        elif "laboratory" in name_l or "lab" in name_l or "research" in name_l or "institute of technology" in name_l:
            return "research_institute"
        elif "university" in name_l or "iit" in name_l or "nit" in name_l or "iiit" in name_l or "iiser" in name_l:
            return "university"
        elif "hospital" in name_l or "aiims" in name_l or "medical" in name_l:
            return "hospital"
        elif "corporation" in name_l or "ltd" in name_l or "limited" in name_l or "psu" in name_l:
            return "psu"
        elif "mission" in name_l:
            return "mission"
        elif "society" in name_l:
            return "autonomous_body"
        elif "municipal" in name_l or "nagar" in name_l:
            return "municipal_body"
        elif "district" in name_l or "collector" in name_l or "drda" in name_l:
            return "district_administration"
        return "other"

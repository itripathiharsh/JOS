"""
Government Job Source Discovery — Authoritative State Departments & Missions Directory
Maps key state departments (Health & Family Welfare, Technical Education, Higher Education,
Rural Development, Skill Development, Energy & Power) across Indian States and UTs.
"""

from typing import Dict, Any

STATE_DEPARTMENTS_REGISTRY: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # ANDHRA PRADESH
    # =========================================================================
    "Health Department (Andhra Pradesh)": {
        "organisation_name": "Department of Health, Medical and Family Welfare, Andhra Pradesh",
        "state": "Andhra Pradesh",
        "official_domain": "hmfw.ap.gov.in",
        "career_url": "https://hmfw.ap.gov.in/notifications.aspx",
        "recruitment_url": "https://hmfw.ap.gov.in/notifications.aspx",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "National Health Mission (Andhra Pradesh)": {
        "organisation_name": "National Health Mission, Andhra Pradesh",
        "state": "Andhra Pradesh",
        "official_domain": "cfw.ap.nic.in",
        "career_url": "https://cfw.ap.nic.in/recruitment.html",
        "recruitment_url": "https://cfw.ap.nic.in/recruitment.html",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Higher Education Department (Andhra Pradesh)": {
        "organisation_name": "Andhra Pradesh State Council of Higher Education (APSCHE)",
        "state": "Andhra Pradesh",
        "official_domain": "apsche.ap.gov.in",
        "career_url": "https://apsche.ap.gov.in/notifications.php",
        "recruitment_url": "https://apsche.ap.gov.in/notifications.php",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Skill Development Mission (Andhra Pradesh)": {
        "organisation_name": "Andhra Pradesh State Skill Development Corporation (APSSDC)",
        "state": "Andhra Pradesh",
        "official_domain": "apssdc.in",
        "career_url": "https://www.apssdc.in/home/careers",
        "recruitment_url": "https://www.apssdc.in/home/careers",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Andhra Pradesh)": {
        "organisation_name": "Transmission Corporation of Andhra Pradesh (APTRANSCO)",
        "state": "Andhra Pradesh",
        "official_domain": "aptransco.co.in",
        "career_url": "https://aptransco.co.in/careers.html",
        "recruitment_url": "https://aptransco.co.in/careers.html",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # MAHARASHTRA
    # =========================================================================
    "Health Department (Maharashtra)": {
        "organisation_name": "Public Health Department, Maharashtra (Arogya Vibhag)",
        "state": "Maharashtra",
        "official_domain": "arogya.maharashtra.gov.in",
        "career_url": "https://arogya.maharashtra.gov.in/1035/Recruitment",
        "recruitment_url": "https://arogya.maharashtra.gov.in/1035/Recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Higher Education Department (Maharashtra)": {
        "organisation_name": "Directorate of Higher Education, Maharashtra",
        "state": "Maharashtra",
        "official_domain": "dhepune.gov.in",
        "career_url": "https://www.dhepune.gov.in/recruitment",
        "recruitment_url": "https://www.dhepune.gov.in/recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Technical Education Department (Maharashtra)": {
        "organisation_name": "Directorate of Technical Education, Maharashtra (DTE)",
        "state": "Maharashtra",
        "official_domain": "dtemaharashtra.gov.in",
        "career_url": "https://www.dtemaharashtra.gov.in/recruitment.html",
        "recruitment_url": "https://www.dtemaharashtra.gov.in/recruitment.html",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Maharashtra)": {
        "organisation_name": "Maharashtra State Electricity Distribution Company (MSEDCL / Mahavitaran)",
        "state": "Maharashtra",
        "official_domain": "mahadiscom.in",
        "career_url": "https://www.mahadiscom.in/en/recruitment-notices/",
        "recruitment_url": "https://www.mahadiscom.in/en/recruitment-notices/",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # KARNATAKA
    # =========================================================================
    "Health Department (Karnataka)": {
        "organisation_name": "Health & Family Welfare Services, Karnataka",
        "state": "Karnataka",
        "official_domain": "hfw.karnataka.gov.in",
        "career_url": "https://hfw.karnataka.gov.in/en/notification/recruitment",
        "recruitment_url": "https://hfw.karnataka.gov.in/en/notification/recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Technical Education Department (Karnataka)": {
        "organisation_name": "Department of Technical Education, Karnataka (DTE)",
        "state": "Karnataka",
        "official_domain": "dtek.karnataka.gov.in",
        "career_url": "https://dtek.karnataka.gov.in/en/notification/recruitment",
        "recruitment_url": "https://dtek.karnataka.gov.in/en/notification/recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Karnataka)": {
        "organisation_name": "Karnataka Power Transmission Corporation Limited (KPTCL)",
        "state": "Karnataka",
        "official_domain": "kptcl.karnataka.gov.in",
        "career_url": "https://kptcl.karnataka.gov.in/en/recruitment",
        "recruitment_url": "https://kptcl.karnataka.gov.in/en/recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # UTTAR PRADESH
    # =========================================================================
    "Health Department (Uttar Pradesh)": {
        "organisation_name": "Department of Medical Health & Family Welfare, Uttar Pradesh",
        "state": "Uttar Pradesh",
        "official_domain": "uphealth.up.gov.in",
        "career_url": "http://uphealth.up.gov.in/en/page/recruitment",
        "recruitment_url": "http://uphealth.up.gov.in/en/page/recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "National Health Mission (Uttar Pradesh)": {
        "organisation_name": "National Health Mission, Uttar Pradesh (UP NHM)",
        "state": "Uttar Pradesh",
        "official_domain": "upnrhm.gov.in",
        "career_url": "http://upnrhm.gov.in/Home/Updates",
        "recruitment_url": "http://upnrhm.gov.in/Home/Updates",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Higher Education Department (Uttar Pradesh)": {
        "organisation_name": "Department of Higher Education, Uttar Pradesh",
        "state": "Uttar Pradesh",
        "official_domain": "uphed.gov.in",
        "career_url": "http://uphed.gov.in/en/page/recruitment",
        "recruitment_url": "http://uphed.gov.in/en/page/recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Uttar Pradesh)": {
        "organisation_name": "Uttar Pradesh Power Corporation Limited (UPPCL)",
        "state": "Uttar Pradesh",
        "official_domain": "uppcl.org",
        "career_url": "https://www.upenergy.in/uppcl/en/page/vacancy-results",
        "recruitment_url": "https://www.upenergy.in/uppcl/en/page/vacancy-results",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # TAMIL NADU
    # =========================================================================
    "Health Department (Tamil Nadu)": {
        "organisation_name": "Health and Family Welfare Department, Tamil Nadu",
        "state": "Tamil Nadu",
        "official_domain": "tnhealth.tn.gov.in",
        "career_url": "https://tnhealth.tn.gov.in/tnhfw/recruitment.php",
        "recruitment_url": "https://tnhealth.tn.gov.in/tnhfw/recruitment.php",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Medical Services Recruitment Board (Tamil Nadu MRB)": {
        "organisation_name": "Medical Services Recruitment Board (TN MRB)",
        "state": "Tamil Nadu",
        "official_domain": "mrb.tn.gov.in",
        "career_url": "http://www.mrb.tn.gov.in/notifications.html",
        "recruitment_url": "http://www.mrb.tn.gov.in/notifications.html",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Tamil Nadu)": {
        "organisation_name": "Tamil Nadu Generation and Distribution Corporation (TANGEDCO)",
        "state": "Tamil Nadu",
        "official_domain": "tangedco.gov.in",
        "career_url": "https://www.tangedco.gov.in/directrecruitment.html",
        "recruitment_url": "https://www.tangedco.gov.in/directrecruitment.html",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # GUJARAT
    # =========================================================================
    "Health Department (Gujarat)": {
        "organisation_name": "Health and Family Welfare Department, Gujarat",
        "state": "Gujarat",
        "official_domain": "gujhealth.gujarat.gov.in",
        "career_url": "https://gujhealth.gujarat.gov.in/recruitment.htm",
        "recruitment_url": "https://gujhealth.gujarat.gov.in/recruitment.htm",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Gujarat)": {
        "organisation_name": "Gujarat Urja Vikas Nigam Limited (GUVNL)",
        "state": "Gujarat",
        "official_domain": "guvnl.com",
        "career_url": "https://www.guvnl.com/careers.php",
        "recruitment_url": "https://www.guvnl.com/careers.php",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # RAJASTHAN
    # =========================================================================
    "Health Department (Rajasthan)": {
        "organisation_name": "Medical, Health & Family Welfare Department, Rajasthan",
        "state": "Rajasthan",
        "official_domain": "rajswasthya.nic.in",
        "career_url": "http://rajswasthya.nic.in/Recruitment.htm",
        "recruitment_url": "http://rajswasthya.nic.in/Recruitment.htm",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Rajasthan)": {
        "organisation_name": "Rajasthan Rajya Vidyut Prasaran Nigam (RVPN)",
        "state": "Rajasthan",
        "official_domain": "energy.rajasthan.gov.in",
        "career_url": "https://energy.rajasthan.gov.in/rvpnl/recruitment",
        "recruitment_url": "https://energy.rajasthan.gov.in/rvpnl/recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # MADHYA PRADESH
    # =========================================================================
    "Health Department (Madhya Pradesh)": {
        "organisation_name": "Public Health and Medical Education, Madhya Pradesh",
        "state": "Madhya Pradesh",
        "official_domain": "health.mp.gov.in",
        "career_url": "http://health.mp.gov.in/en/recruitment",
        "recruitment_url": "http://health.mp.gov.in/en/recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Madhya Pradesh)": {
        "organisation_name": "MP Power Management Company Limited (MPPMCL)",
        "state": "Madhya Pradesh",
        "official_domain": "mppmcl.com",
        "career_url": "https://mppmcl.com/careers/",
        "recruitment_url": "https://mppmcl.com/careers/",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # WEST BENGAL
    # =========================================================================
    "Health Department (West Bengal)": {
        "organisation_name": "Department of Health & Family Welfare, West Bengal",
        "state": "West Bengal",
        "official_domain": "wbhealth.gov.in",
        "career_url": "https://www.wbhealth.gov.in/pages/career",
        "recruitment_url": "https://www.wbhealth.gov.in/pages/career",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "West Bengal Health Recruitment Board (WBHRB)": {
        "organisation_name": "West Bengal Health Recruitment Board (WBHRB)",
        "state": "West Bengal",
        "official_domain": "wbhrb.in",
        "career_url": "https://wbhrb.in/advertisement",
        "recruitment_url": "https://wbhrb.in/advertisement",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # KERALA
    # =========================================================================
    "Health Department (Kerala)": {
        "organisation_name": "Directorate of Health Services, Kerala",
        "state": "Kerala",
        "official_domain": "dhs.kerala.gov.in",
        "career_url": "https://dhs.kerala.gov.in/vacancies/",
        "recruitment_url": "https://dhs.kerala.gov.in/vacancies/",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Kerala)": {
        "organisation_name": "Kerala State Electricity Board (KSEB)",
        "state": "Kerala",
        "official_domain": "kseb.in",
        "career_url": "https://www.kseb.in/index.php?option=com_content&view=article&id=51&Itemid=599&lang=en",
        "recruitment_url": "https://www.kseb.in/index.php?option=com_content&view=article&id=51&Itemid=599&lang=en",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # BIHAR
    # =========================================================================
    "Health Department (Bihar)": {
        "organisation_name": "State Health Society Bihar (SHSB)",
        "state": "Bihar",
        "official_domain": "statehealthsocietybihar.org",
        "career_url": "http://statehealthsocietybihar.org/careers.html",
        "recruitment_url": "http://statehealthsocietybihar.org/careers.html",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Bihar)": {
        "organisation_name": "Bihar State Power Holding Company Limited (BSPHCL)",
        "state": "Bihar",
        "official_domain": "bsphcl.co.in",
        "career_url": "https://bsphcl.co.in/NoticeBoard.aspx",
        "recruitment_url": "https://bsphcl.co.in/NoticeBoard.aspx",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # ODISHA
    # =========================================================================
    "Health Department (Odisha)": {
        "organisation_name": "Health & Family Welfare Department, Odisha",
        "state": "Odisha",
        "official_domain": "health.odisha.gov.in",
        "career_url": "https://health.odisha.gov.in/notifications/recruitment",
        "recruitment_url": "https://health.odisha.gov.in/notifications/recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Power Department (Odisha)": {
        "organisation_name": "Odisha Power Transmission Corporation Limited (OPTCL)",
        "state": "Odisha",
        "official_domain": "optcl.co.in",
        "career_url": "https://www.optcl.co.in/CurrentOpening.aspx",
        "recruitment_url": "https://www.optcl.co.in/CurrentOpening.aspx",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # PUNJAB & HARYANA
    # =========================================================================
    "Health Department (Punjab)": {
        "organisation_name": "Health & Family Welfare Department, Punjab",
        "state": "Punjab",
        "official_domain": "health.punjab.gov.in",
        "career_url": "https://health.punjab.gov.in/?q=recruitment",
        "recruitment_url": "https://health.punjab.gov.in/?q=recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Health Department (Haryana)": {
        "organisation_name": "Health Department, Haryana",
        "state": "Haryana",
        "official_domain": "haryanahealth.gov.in",
        "career_url": "http://haryanahealth.gov.in/en/vacancies",
        "recruitment_url": "http://haryanahealth.gov.in/en/vacancies",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },

    # =========================================================================
    # ASSAM & TELANGANA
    # =========================================================================
    "Health Department (Assam)": {
        "organisation_name": "National Health Mission, Assam",
        "state": "Assam",
        "official_domain": "nhm.assam.gov.in",
        "career_url": "https://nhm.assam.gov.in/portlets/recruitment",
        "recruitment_url": "https://nhm.assam.gov.in/portlets/recruitment",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
    "Health Department (Telangana)": {
        "organisation_name": "Health, Medical & Family Welfare Department, Telangana",
        "state": "Telangana",
        "official_domain": "chfw.telangana.gov.in",
        "career_url": "https://chfw.telangana.gov.in/notifications.do",
        "recruitment_url": "https://chfw.telangana.gov.in/notifications.do",
        "source_type": "portal",
        "government_level": "state",
        "confidence_category": "AUTHORITATIVE",
    },
}

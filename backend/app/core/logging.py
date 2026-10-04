import os
import re
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.core.config import settings


class SecretMaskingFilter(logging.Filter):
    """Filters passwords, bearer tokens, API keys, and credentials from log records."""
    PATTERNS = [
        # Database URL passwords
        (re.compile(r':([^@/\s]+)@', re.IGNORECASE), r':****@'),
        # Bearer tokens
        (re.compile(r'(Bearer\s+)[A-Za-z0-9_\-\.]{6,}', re.IGNORECASE), r'\1****'),
        # Basic auth headers
        (re.compile(r'(Authorization:\s*Basic\s+)[A-Za-z0-9+/=]+', re.IGNORECASE), r'\1****'),
        # Key-value assignments (password=..., api_key=..., secret=...)
        (re.compile(r'((?:password|secret|token|api_key|access_token)\s*=\s*)[^\s,;&]+', re.IGNORECASE), r'\1****'),
        # JSON field values ("password": "...", "secret": "...")
        (re.compile(r'("(?:password|secret|token|api_key|access_token)"\s*:\s*)"[^"]+"', re.IGNORECASE), r'\1"****"'),
        # URL query string parameters (?password=..., &token=...)
        (re.compile(r'([?&](?:password|token|key|secret)=)[^&\s]+', re.IGNORECASE), r'\1****'),
    ]

    def mask_text(self, text: str) -> str:
        for pattern, replacement in self.PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.mask_text(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.mask_text(str(a)) if isinstance(a, str) else a for a in record.args)
        return True


def setup_logging(log_filename: str = "backend.log"):
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handlers = [
        logging.StreamHandler(sys.stdout)
    ]

    # File logging on F: Drive
    try:
        log_dir = Path(settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / log_filename

        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10 MB per log file
            backupCount=5,
            encoding="utf-8"
        )
        handlers.append(file_handler)
    except Exception as e:
        print(f"Warning: Failed to initialize file logger: {e}", file=sys.stderr)

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True
    )

    mask_filter = SecretMaskingFilter()
    for h in logging.root.handlers:
        h.addFilter(mask_filter)

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("job_agent")

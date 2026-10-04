"""
Job Operating System - Local Sandboxed Browser Engine (Playwright)
100% Local, Strict F: Drive Isolation.
Handles browser navigation, form inspection, screenshot capture, and session persistence.
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone

# Ensure paths
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.core.config import settings
from browser.base import BrowserAutomationEngine

# Enforce Playwright browser path on F: Drive before importing playwright
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = settings.PLAYWRIGHT_BROWSERS_PATH

logger = logging.getLogger("browser_engine")


class LocalBrowserEngine(BrowserAutomationEngine):
    """
    Playwright Chromium automation engine with local profile persistence
    and screenshot storage on F: drive.
    """

    def __init__(
        self,
        headless: bool = None,
        session_name: str = "candidate_session",
    ):
        self.headless = settings.PLAYWRIGHT_HEADLESS if headless is None else headless
        self.session_name = session_name
        self.browser_dir = Path(settings.BROWSER_DATA_DIR)
        self.screenshots_dir = Path(settings.STORAGE_DIR) / "screenshots"

        self.browser_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def start(self):
        """Starts Playwright and launches Chromium."""
        from playwright.sync_api import sync_playwright

        if self._playwright is None:
            self._playwright = sync_playwright().start()

        session_state_file = self.browser_dir / f"{self.session_name}_state.json"

        launch_args = [
            "--no-default-browser-check",
            "--disable-extensions",
        ]

        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
            timeout=settings.BROWSER_TIMEOUT_MS,
        )

        context_kwargs = {
            "viewport": {"width": 1280, "height": 900},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "accept_downloads": True,
        }

        if session_state_file.exists():
            context_kwargs["storage_state"] = str(session_state_file)

        self._context = self._browser.new_context(**context_kwargs)
        self._page = self._context.new_page()
        logger.info(f"Local browser started (headless={self.headless}, session={self.session_name})")

    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigates to URL and captures title, HTML content, and screenshot."""
        from app.core.security import is_safe_external_url
        is_safe, block_reason = is_safe_external_url(url)
        if not is_safe:
            logger.warning(f"Browser navigation blocked by security policy for URL '{url}': {block_reason}")
            raise ValueError(f"Browser navigation blocked by security policy: {block_reason}")

        if not self._page:
            self.start()

        logger.info(f"Navigating to {url}")
        response = self._page.goto(url, wait_until="domcontentloaded", timeout=settings.BROWSER_TIMEOUT_MS)

        status_code = response.status if response else 200
        title = self._page.title()
        html_content = self._page.content()

        return {
            "url": self._page.url,
            "status_code": status_code,
            "title": title,
            "html_content": html_content,
        }

    def save_screenshot(self, tag: str = "checkpoint") -> Optional[str]:
        """Captures page screenshot to F: drive storage."""
        if not self._page:
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{tag}.png"
        target_path = self.screenshots_dir / filename

        try:
            self._page.screenshot(path=str(target_path), full_page=False)
            logger.info(f"Saved screenshot: {target_path}")
            return str(target_path)
        except Exception as e:
            logger.warning(f"Could not take screenshot: {e}")
            return None

    def save_session_state(self):
        """Persists cookies and local storage for authentication recovery."""
        if self._context:
            session_state_file = self.browser_dir / f"{self.session_name}_state.json"
            self._context.storage_state(path=str(session_state_file))
            logger.info(f"Saved browser session state to {session_state_file}")

    def close(self):
        """Cleanly releases all browser resources."""
        try:
            if self._context:
                self.save_session_state()
            if self._page:
                self._page.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error while closing browser resources: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            logger.info("Local browser engine closed.")


def check_browser_readiness() -> Tuple[bool, str]:
    """Pre-flight check to verify Playwright Chromium engine availability."""
    try:
        engine = LocalBrowserEngine(headless=True)
        res = engine.navigate("https://example.com")
        engine.close()
        if "Example Domain" in res.get("title", ""):
            return True, "Playwright Chromium engine verified and ready on F: drive."
        return False, f"Unexpected title: {res.get('title')}"
    except Exception as e:
        return False, f"Playwright verification failed: {str(e)}"

from abc import ABC, abstractmethod


class BrowserAutomationEngine(ABC):
    """
    Abstract interface for future sandboxed browser automation (Playwright/Puppeteer).
    Implementation scheduled for future phases.
    """
    @abstractmethod
    def navigate(self, url: str):
        pass

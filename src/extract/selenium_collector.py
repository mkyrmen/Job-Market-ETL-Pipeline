"""Optional browser-based collector (Selenium).

Not used by default. This module exists so the project can also demonstrate
browser automation for JavaScript-rendered sources and can serve as a
fallback if the site's server-rendered payload changes in a way the HTTPS
parser cannot follow. It requires ``selenium`` and ``webdriver-manager``
(see ``requirements-dev.txt``).
"""

from __future__ import annotations

import logging
from datetime import datetime

from src.extract.base import ExtractionResult
from src.extract.google_careers import SEARCH_URL, parse_google_payload

logger = logging.getLogger(__name__)


class SeleniumGoogleCareersCollector:
    """Browser-based collector with a controlled, respectful access profile.

    Launches Chrome headlessly by default, visits the public careers search
    results, waits for the server-rendered payload and reuses the same
    payload parser as the HTTPS extractor.
    """

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless

    def extract(self, query: str, limit: int | None = None) -> ExtractionResult:
        try:
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium import webdriver
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Selenium collector requires 'selenium' and 'webdriver-manager'"
            ) from exc

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        result = ExtractionResult(source="google_careers", query=query)
        try:
            url = f"{SEARCH_URL}?q={query}&hl=en_US&page_number=1"
            logger.info("Selenium: fetching %s", url)
            driver.get(url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "title"))
            )
            html = driver.page_source
            page_records = parse_google_payload(html, query=query)
            result.records.extend(page_records)
            result.pages_fetched = 1
            logger.info("Selenium collector parsed %d records", len(page_records))
        except Exception:  # noqa: BLE001 - surface browser failures loudly
            logger.exception("Selenium collection failed")
            raise
        finally:
            driver.quit()
        return result
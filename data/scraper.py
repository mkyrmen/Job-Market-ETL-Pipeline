import pandas as pd
import sqlite3
import time
import os
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class JobPipeline:
    def __init__(self, job_query):
        self.job_query = job_query
        self.db_path = "Z:/Project/Job_Scraper/data/jobs_database.db"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.raw_data = []
        self.driver = self._setup_driver()

    def _setup_driver(self):
        options = Options()
        # MASTER LEVEL STEALTH
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # Adding a real User-Agent is the #1 fix for Google timeouts
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

import pandas as pd
import sqlite3
import time
import os
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class JobPipeline:
    def __init__(self, job_query):
        self.job_query = job_query
        self.db_path = "Z:/Project/Job_Scraper/data/jobs_database.db"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.raw_data = []
        self.driver = self._setup_driver()

    def _setup_driver(self):
        options = Options()
        # MASTER LEVEL STEALTH
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # Adding a real User-Agent is the #1 fix for Google timeouts
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def extract_data(self, limit=5):
        try:
            print(f"🔍 Accessing Google Careers for: {self.job_query}")
            url = f"https://www.google.com/about/careers/applications/jobs/results/?q={self.job_query}"
            self.driver.get(url)

            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "h3")))
            time.sleep(5) 

            # Find titles inside the list items
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, "li h3")
            print(f"📊 Potential job cards detected: {len(job_cards)}")

            for i in range(min(limit, len(job_cards))):
                try:
                    # Re-find to avoid Stale Elements
                    current_cards = self.driver.find_elements(By.CSS_SELECTOR, "li h3")
                    card = current_cards[i]
                    title = card.text.strip()

                    # Click and wait
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", card)
                    print(f"🖱️  Clicked: {title}")

                    # --- THE FIX: WAIT FOR THE RIGHT PANEL ---
                    # Instead of a class, we look for the element that has 'Description' text
                    time.sleep(3) 
                    
                    # We grab the body of the page and find the largest text block that isn't the sidebar
                    # Google's job detail container usually has a specific 'aria-label'
                    try:
                        desc_container = wait.until(EC.presence_of_element_located(
                            (By.XPATH, "//div[@role='main'] | //section[contains(@aria-label, 'Job details')]")
                        ))
                        desc = desc_container.text
                    except:
                        # Fallback: Just grab the largest div on the page that isn't the list
                        desc = self.driver.find_element(By.TAG_NAME, "body").text

                    if len(desc) < 100:
                        raise Exception("Description too short, likely failed to load.")

                    self.raw_data.append({
                        "query": self.job_query,
                        "title": title,
                        "description": desc,
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

                    print(f"✅ Extracted: {title}")

                except Exception as e:
                    print(f"⚠️ Card {i} failed: The right-side panel didn't load in time.")
                    continue

        except Exception as e:
            print(f"❌ Critical Error: {e}")
        finally:
            self.driver.quit()

    def transform_and_load(self):
        if not self.raw_data:
            print("❌ No data extracted.")
            return

        df = pd.DataFrame(self.raw_data)
        conn = sqlite3.connect(self.db_path)
        df.to_sql("jobs", conn, if_exists="append", index=False)
        conn.close()
        print(f"💾 Saved {len(df)} jobs to SQLite database at {self.db_path}")

if __name__ == "__main__":
    pipeline = JobPipeline("Data Analyst")
    pipeline.extract_data(limit=5)
    pipeline.transform_and_load()

    def transform_and_load(self):
        if not self.raw_data:
            print("❌ No data extracted.")
            return

        df = pd.DataFrame(self.raw_data)
        conn = sqlite3.connect(self.db_path)
        df.to_sql("jobs", conn, if_exists="append", index=False)
        conn.close()
        print(f"💾 Saved {len(df)} jobs to SQLite database at {self.db_path}")

if __name__ == "__main__":
    pipeline = JobPipeline("Data Analyst")
    pipeline.extract_data(limit=5)
    pipeline.transform_and_load()
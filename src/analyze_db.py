import sqlite3
import pandas as pd

def run_analysis():
    db_path = "Z:/Project/Job_Scraper/data/jobs_database.db"
    conn = sqlite3.connect(db_path)
    
    print("📋 --- DATABASE SUMMARY ---")
    
    # 1. Total records count
    total = pd.read_sql("SELECT COUNT(*) as total FROM jobs", conn)
    print(f"Total jobs collected: {total['total'][0]}")
    
    # 2. View the most recent entries
    recent = pd.read_sql("SELECT title, scraped_at FROM jobs ORDER BY scraped_at DESC LIMIT 5", conn)
    print("\nMost Recent Scrapes:")
    print(recent)
    
    # 3. Simple Keyword Search (Looking for 'Senior' vs 'Junior')
    senior_count = pd.read_sql("SELECT COUNT(*) as count FROM jobs WHERE description LIKE '%Senior%'", conn)
    print(f"\nJobs mentioning 'Senior' in description: {senior_count['count'][0]}")
    
    conn.close()

if __name__ == "__main__":
    run_analysis()
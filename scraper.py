import requests
import os
import sqlite3
from datetime import datetime

WORKDAY_URL = "https://wd1.myworkdaysite.com/wday/cxs/wf/WellsFargoJobs/jobs"

LOCATION_FILTER = "Hyderabad"
MAX_PAGES = 2
MAX_DAYS = 7

KEYWORDS = [
    "Data",
    "Analytics",
    "Business Intelligence"
]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DB_FILE = "jobs.db"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}


# ---------------- DATABASE ---------------- #

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT,
            location TEXT,
            posted_on TEXT,
            apply_url TEXT,
            first_seen TEXT
        )
    """)

    conn.commit()
    conn.close()


def insert_job(job):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO jobs (job_id, title, location, posted_on, apply_url, first_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            job["externalPath"],
            job["title"],
            job["locationsText"],
            job["postedOn"],
            f"https://wd1.myworkdaysite.com{job['externalPath']}",
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()
        return True  # New job inserted

    except sqlite3.IntegrityError:
        conn.close()
        return False  # Duplicate


# ---------------- WORKDAY ---------------- #

def fetch_jobs(keyword, offset=0):
    payload = {
        "limit": 20,
        "offset": offset,
        "searchText": keyword
    }

    r = requests.post(WORKDAY_URL, headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()


def is_recent(posted_text):
    if not posted_text:
        return False

    text = posted_text.lower()

    if "today" in text or "yesterday" in text:
        return True

    if "day" in text:
        try:
            if "+" in text:
                return False
            days = int(text.split()[1])
            return days <= MAX_DAYS
        except:
            return False

    return False


def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    requests.post(url, json=payload)


# ---------------- MAIN ---------------- #

def main():
    print("Initializing database...")
    init_db()

    print("Checking latest Hyderabad jobs...")

    for keyword in KEYWORDS:
        offset = 0
        page_count = 0

        while page_count < MAX_PAGES:
            data = fetch_jobs(keyword, offset)
            jobs = data.get("jobPostings", [])

            if not jobs:
                break

            for job in jobs:
                location = job.get("locationsText", "")
                posted = job.get("postedOn", "")

                if LOCATION_FILTER.lower() in location.lower() and is_recent(posted):

                    is_new = insert_job(job)

                    if is_new:
                        print(f"New job found: {job['title']}")

                        message = f"""
<b>New Wells Fargo Job (Hyderabad)</b>

Title: {job['title']}
Location: {location}
Posted: {posted}
Apply: https://wd1.myworkdaysite.com{job['externalPath']}
"""
                        send_telegram(message)

            offset += 20
            page_count += 1

    print("Done.")


if __name__ == "__main__":
    main()

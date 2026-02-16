import requests
import os
import json

BASE_URL = "https://www.wellsfargojobs.com/"
LANG = "en-US"
LOCATION = os.getenv("JOB_LOCATION", "Hyderabad")

KEYWORDS = [
    "Data Analyst",
    "Business Intelligence",
    "BI Analyst",
    "Analytics",
    "Reporting",
    "Power BI",
    "SQL",
    "Databricks",
    "Azure",
    "Data Engineer",
    "ETL"
]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "jobs.json"


def fetch_jobs(keyword, page=1):
    url = f"{BASE_URL}{LANG}/search?keyword={keyword}&location={LOCATION}&page={page}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def get_all_jobs():
    all_jobs = []
    seen = set()

    for keyword in KEYWORDS:
        page = 1
        first = fetch_jobs(keyword, page)

        total_pages = first["searchResults"]["totalPages"]
        jobs = first["searchResults"]["jobs"]

        for job in jobs:
            if job["externalPath"] not in seen:
                all_jobs.append(job)
                seen.add(job["externalPath"])

        while page < total_pages:
            page += 1
            data = fetch_jobs(keyword, page)
            for job in data["searchResults"]["jobs"]:
                if job["externalPath"] not in seen:
                    all_jobs.append(job)
                    seen.add(job["externalPath"])

    return all_jobs


def load_previous():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return []


def save_current(jobs):
    with open(STATE_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)


def detect_new_jobs(old_jobs, new_jobs):
    old_ids = {job["externalPath"] for job in old_jobs}
    return [job for job in new_jobs if job["externalPath"] not in old_ids]


def main():
    new_jobs = get_all_jobs()
    old_jobs = load_previous()

    new_entries = detect_new_jobs(old_jobs, new_jobs)

    if new_entries:
        for job in new_entries[:5]:
            msg = f"""
<b>New Wells Fargo Job (Hyderabad)</b>

Title: {job['title']}
Location: {job['locations']}
Posted: {job['postedDate']}
Apply: https://www.wellsfargojobs.com{job['externalPath']}
"""
            send_telegram(msg)

    save_current(new_jobs)


if __name__ == "__main__":
    main()

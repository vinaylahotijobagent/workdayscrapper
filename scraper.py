import requests
import os
import json
import time

WORKDAY_URL = "https://wd1.myworkdaysite.com/wday/cxs/wf/WellsFargoJobs/jobs"

LOCATION_FILTER = "Hyderabad"

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

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}


def fetch_jobs(keyword, offset=0):
    payload = {
        "limit": 20,
        "offset": offset,
        "searchText": keyword
    }

    response = requests.post(WORKDAY_URL, headers=HEADERS, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def get_all_jobs():
    all_jobs = []
    seen = set()

    for keyword in KEYWORDS:
        offset = 0

        while True:
            data = fetch_jobs(keyword, offset)
            jobs = data.get("jobPostings", [])

            if not jobs:
                break

            for job in jobs:
                job_id = job.get("externalPath")

                # Filter Hyderabad manually
                locations = job.get("locationsText", [])
                location_text = " ".join(locations)

                if LOCATION_FILTER.lower() in location_text.lower():
                    if job_id and job_id not in seen:
                        all_jobs.append(job)
                        seen.add(job_id)

            offset += 20
            time.sleep(0.5)

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
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    requests.post(url, json=payload)


def detect_new_jobs(old_jobs, new_jobs):
    old_ids = {job.get("externalPath") for job in old_jobs}
    return [job for job in new_jobs if job.get("externalPath") not in old_ids]


def main():
    new_jobs = get_all_jobs()
    old_jobs = load_previous()

    new_entries = detect_new_jobs(old_jobs, new_jobs)

    if new_entries:
        for job in new_entries[:5]:
            title = job.get("title", "N/A")
            location = ", ".join(job.get("locationsText", []))
            posted = job.get("postedOn", "N/A")
            apply_url = f"https://wd1.myworkdaysite.com{job.get('externalPath')}"

            message = f"""
<b>New Wells Fargo Job (Hyderabad)</b>

Title: {title}
Location: {location}
Posted: {posted}
Apply: {apply_url}
"""
            send_telegram(message)

    save_current(new_jobs)


if __name__ == "__main__":
    main()

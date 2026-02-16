import requests
import os
import json

WORKDAY_URL = "https://wd1.myworkdaysite.com/wday/cxs/wf/WellsFargoJobs/jobs"

LOCATION_FILTER = "Hyderabad"
MAX_PAGES = 2
MAX_DAYS = 5

KEYWORDS = [
    "Data",
    "Analytics",
    "Business Intelligence"
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


def get_all_jobs():
    all_jobs = []
    seen = set()

    for keyword in KEYWORDS:
        offset = 0
        page_count = 0

        while page_count < MAX_PAGES:
            data = fetch_jobs(keyword, offset)
            jobs = data.get("jobPostings", [])

            if not jobs:
                break

            for job in jobs:
                job_id = job.get("externalPath")
                location_text = job.get("locationsText", "")
                posted = job.get("postedOn", "")

                if (
                    job_id
                    and job_id not in seen
                    and LOCATION_FILTER.lower() in location_text.lower()
                    and is_recent(posted)
                ):
                    all_jobs.append(job)
                    seen.add(job_id)

            offset += 20
            page_count += 1

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
    print("Checking latest Hyderabad data jobs...")

    new_jobs = get_all_jobs()
    old_jobs = load_previous()

    print(f"Filtered jobs found: {len(new_jobs)}")

    new_entries = detect_new_jobs(old_jobs, new_jobs)

    if new_entries:
        print(f"New jobs detected: {len(new_entries)}")
        for job in new_entries:
            title = job.get("title", "N/A")
            location = job.get("locationsText", "")
            posted = job.get("postedOn", "")
            apply_url = f"https://wd1.myworkdaysite.com{job.get('externalPath')}"

            message = f"""
<b>New Wells Fargo Job (Hyderabad)</b>

Title: {title}
Location: {location}
Posted: {posted}
Apply: {apply_url}
"""
            send_telegram(message)
    else:
        print("No new jobs found.")

    save_current(new_jobs)


if __name__ == "__main__":
    main()

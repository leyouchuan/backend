import os
import json
import ast
import time
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from newsapi.newsapi_client import NewsApiClient
from random import randrange
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
from dotenv import load_dotenv
from utils.utiles import add_location_info

load_dotenv()
router = APIRouter()

COUNTRIES_LANGUAGES = {
    "in": "en", "us": "en", "au": "en", "ru": "ru", 
    "fr": "fr", "gb": "en", "cn": "zh"
}
CATEGORIES = [
    "business", "entertainment", "general", 
    "health", "science", "sports", "technology"
]
SOURCES = ["bbc.co.uk", "cnn.com", "foxnews.com", "google.com"]

API_KEYS = os.getenv("API_KEYS").split(',')
print("解析后的apikey=",API_KEYS)
LAST_KEY_INDEX = randrange(0, len(API_KEYS))

def get_key():
    global LAST_KEY_INDEX
    LAST_KEY_INDEX = (LAST_KEY_INDEX + 1) % len(API_KEYS)
    return API_KEYS[LAST_KEY_INDEX]

def save_to_json(filename, new_content):
    filtered_articles = add_location_info(new_content['articles'])

    if not filtered_articles:
        print("No articles with location found, nothing to save.")
        return

    data = {"status": "ok", "totalResults": 0, "articles": []}

    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"{filename} is empty or corrupted, reinitializing.")

    data["articles"].extend(filtered_articles)
    data["totalResults"] = len(data["articles"])

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(filtered_articles)} articles with location to {filename}.")

def update_top_headline():
    for category in CATEGORIES:
        for country in COUNTRIES_LANGUAGES:
            print(f"Started updating category: {category} country: {country} at: {time.strftime('%A, %d. %B %Y %I:%M:%S %p')}")
            newsapi = NewsApiClient(api_key=get_key())
            top_headlines = newsapi.get_top_headlines(category=category, page_size=100)
            save_to_json(f"data/top-headlines/category/{category}.json", top_headlines)
    print("Top headlines updated.")

def update_everything():
    newsapi = NewsApiClient(api_key=get_key())
    for source in SOURCES:
        print(f"Started updating source: {source} at: {time.strftime('%A, %d. %B %Y %I:%M:%S %p')}")
        all_articles = newsapi.get_everything(
            sources=source,
            from_param=(datetime.now() - timedelta(hours=12, minutes=30)).date().isoformat(),
            language='en',
            sort_by='publishedAt',
            page_size=100
        )
        save_to_json(f"data/everything/{source}.json", all_articles)
    print("Everything updated.")

@router.get("/top-headlines/update")
async def update_top_headline_api():
    update_top_headline()
    return {"status": "updated"}

@router.get("/everything/update")
async def update_everything_api():
    update_everything()
    return {"status": "updated"}


# Scheduler setup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()  # 使用 AsyncIO 版本的调度器
scheduler.start()
INTERVAL = 1  # 更新间隔，单位为分钟
scheduler.add_job(update_everything, trigger="interval", minutes=INTERVAL)  # 直接传异步函数即可
scheduler.add_job(update_top_headline, trigger="interval", minutes=INTERVAL)

#每日五点更新：
scheduler.add_job(
    func=update_top_headline,
    trigger=CronTrigger(hour=5, minute=0),
)

scheduler.add_job(
    func=update_everything,
    trigger=CronTrigger(hour=5, minute=0),
)

if not scheduler.running:
    scheduler.start()
atexit.register(lambda: scheduler.shutdown())
print("Scheduler started.")
import os
import json
import ast
import time
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from newsapi import NewsApiClient
from random import randrange
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from routers.newsapi.utiles import add_location_info
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from db import database
from models import articles, article_locations


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
SOURCES = ["bbc-news", "cnn", "foxnews", "google"]

API_KEYS = ast.literal_eval(os.getenv("API_KEYS"))
LAST_KEY_INDEX = randrange(0, len(API_KEYS))

def get_key():
    global LAST_KEY_INDEX
    LAST_KEY_INDEX = (LAST_KEY_INDEX + 1) % len(API_KEYS)
    return API_KEYS[LAST_KEY_INDEX]


async def save_to_db(new_content, category=None, country=None):
    filtered_articles = add_location_info(new_content['articles'])
    if not filtered_articles:
        print("No articles with location found, nothing to save.")
        return

    for article in filtered_articles:
        # 插入 articles
        avalues = {
            "source_id": article.get("source", {}).get("id"),
            "source_name": article.get("source", {}).get("name"),
            "author": article.get("author"),
            "title": article.get("title"),
            "description": article.get("description"),
            "url": article.get("url"),
            "url_to_image": article.get("urlToImage"),
            "published_at": datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")),
            "content": article.get("content"),
            "category": category,
            "country": country,
        }
        insert_stmt = pg_insert(articles).values(**avalues).on_conflict_do_nothing(index_elements=['url']).returning(articles.c.id)
        article_id = await database.execute(insert_stmt)
        if not article_id: # 已存在，查找id
            query = articles.select().where(articles.c.url == article["url"])
            row = await database.fetch_one(query)
            article_id = row["id"]
        # 插入 location(s)
        locations = article.get("location", [])
        for loc in locations:
            await database.execute(article_locations.insert().values(
                article_id=article_id,
                location_name=loc["location"],
                lat=loc["lat"],
                lng=loc["lng"]
            ))

async def update_top_headline():
    for category in CATEGORIES:
        for country in COUNTRIES_LANGUAGES:
            print(f"Started updating category: {category} country: {country} at: {time.strftime('%A, %d. %B %Y %I:%M:%S %p')}")
            newsapi = NewsApiClient(api_key=get_key())
            top_headlines = newsapi.get_top_headlines(category=category, page_size=100)
            # 使用 await
            await save_to_db(top_headlines, category=category, country=country)
    print("Top headlines updated.")

async def update_everything():
    newsapi = NewsApiClient(api_key=get_key())
    for source in SOURCES:
        print(f"Started updating source: {source} at: {time.strftime('%A, %d. %B %Y %I:%M:%S %p')}")
        all_articles = newsapi.get_everything(
            sources=source,
            from_param=(datetime.now() - timedelta(hours=20, minutes=30)).date().isoformat(),
            language='en',
            sort_by='publishedAt',
            page_size=100
        )
        # 使用 await
        await save_to_db(all_articles, category=None, country=None)
    print("Everything updated.")

@router.get("/top-headlines/update")
async def update_top_headline_api():
    await update_top_headline()
    return {"status": "updated"}

@router.get("/everything/update")
async def update_everything_api():
    await update_everything()
    return {"status": "updated"}


from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()  # 使用 AsyncIO 版本的调度器
scheduler.start()
INTERVAL = 1  # 更新间隔，单位为分钟
scheduler.add_job(update_everything, trigger="interval", minutes=INTERVAL)  # 直接传异步函数即可
scheduler.add_job(update_top_headline, trigger="interval", minutes=INTERVAL)
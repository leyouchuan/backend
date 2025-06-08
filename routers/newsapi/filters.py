import os
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from datetime import datetime, timezone
from models import articles
from db import database

COUNTRIES_LANGUAGES = {
    "in": "en", "us": "en", "au": "en", "ru": "ru", 
    "fr": "fr", "gb": "en", "cn": "zh"
}
CATEGORIES = [
    "business", "entertainment", "general", 
    "health", "science", "sports", "technology"
]
SOURCES = ["bbc.co.uk", "cnn.com", "foxnews.com", "google.com"]

from sqlalchemy import select, and_
from datetime import datetime, timezone

async def filter_by_category(category: str):
    now = datetime.now(timezone.utc)
    past_day = now - timedelta(days=2)

    query = select(articles).where(
        and_(
            articles.c.category == category,
            articles.c.published_at >= past_day,
            articles.c.published_at <= now
        )
    )
    rows = await database.fetch_all(query)
    data = [dict(row) for row in rows]
    return {"totalResults": len(data), "articles": data}

async def filter_by_time(category: str, start_time_str: str, end_time_str: str):
    try:
        start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
        end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
    except Exception as e:
        raise ValueError(f"时间格式错误: {e}")

    query = select(articles).where(
        and_(
            articles.c.category == category,
            articles.c.published_at >= start_time,
            articles.c.published_at <= end_time
        )
    )
    rows = await database.fetch_all(query)
    data = [dict(row) for row in rows]
    return {"totalResults": len(data), "articles": data}

async def filter_all_by_time(start_time_str: str, end_time_str: str):
    try:
        start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
        end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
    except Exception as e:
        raise ValueError(f"时间格式错误: {e}")

    query = select(articles).where(
        and_(
            articles.c.published_at >= start_time,
            articles.c.published_at <= end_time
        )
    )
    rows = await database.fetch_all(query)
    data = [dict(row) for row in rows]
    return {"totalResults": len(data), "articles": data}

async def get_everything_by_source(source: str):
    query = select(articles).where(articles.c.source_name == source)
    rows = await database.fetch_all(query)
    data = [dict(row) for row in rows]
    return {"totalResults": len(data), "articles": data}
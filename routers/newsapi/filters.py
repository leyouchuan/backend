import os
import json
from datetime import datetime, timezone, timedelta

COUNTRIES_LANGUAGES = {
    "in": "en", "us": "en", "au": "en", "ru": "ru", 
    "fr": "fr", "gb": "en", "cn": "zh"
}
CATEGORIES = [
    "business", "entertainment", "general", 
    "health", "science", "sports", "technology"
]
SOURCES = ["bbc.co.uk", "cnn.com", "foxnews.com", "google.com"]

def filter_by_category(category: str):
    """根据类别过滤近2天内的头条新闻"""
    filepath = f"data/top-headlines/category/{category}.json"
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    now = datetime.now(timezone.utc)
    past_day = now - timedelta(days=2)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtered_news = []
    for news in data.get('articles', []):
        pub_time_str = news.get('publishedAt')
        if not pub_time_str:
            continue
        try:
            pub_time = datetime.fromisoformat(pub_time_str.replace("Z", "+00:00"))
        except Exception:
            continue
        if past_day <= pub_time <= now:
            filtered_news.append(news)

    return {"totalResults": len(filtered_news), "articles": filtered_news}

def filter_by_time(category: str, start_time_str: str, end_time_str: str):
    """根据类别和时间范围过滤新闻"""
    filepath = os.path.join("data", "top-headlines", "category", f"{category}.json")
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
        end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
    except Exception as e:
        raise ValueError(f"时间格式错误: {e}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtered_news = []
    for news in data.get("articles", []):
        pub_time = news.get("publishedAt")
        if not pub_time:
            continue
        try:
            pub_time_obj = datetime.fromisoformat(pub_time.replace("Z", "+00:00"))
        except Exception:
            continue
        if start_time <= pub_time_obj <= end_time:
            filtered_news.append(news)

    return {"totalResults": len(filtered_news), "articles": filtered_news}

def filter_all_by_time(start_time_str: str, end_time_str: str):
    """所有类别，根据时间范围过滤新闻"""
    try:
        start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
        end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
    except Exception as e:
        raise ValueError(f"时间格式错误: {e}")

    filtered_news = []

    for category in CATEGORIES:
        filepath = os.path.join("data", "top-headlines", "category", f"{category}.json")
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for news in data.get("articles", []):
            pub_time_str = news.get("publishedAt")
            if not pub_time_str:
                continue
            try:
                pub_time = datetime.fromisoformat(pub_time_str.replace("Z", "+00:00"))
            except Exception:
                continue
            if start_time <= pub_time <= end_time:
                filtered_news.append(news)

    return {"totalResults": len(filtered_news), "articles": filtered_news}

def get_everything_by_source(source: str):
    """获取特定来源的所有文章"""
    filepath = f"data/everything/{source}.json"
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
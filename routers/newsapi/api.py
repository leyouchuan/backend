import os
import json
import ast
import time
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from newsapi import NewsApiClient
from random import randrange
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

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

API_KEYS = ast.literal_eval(os.getenv("API_KEYS"))
LAST_KEY_INDEX = randrange(0, len(API_KEYS))

def get_key():
    """获取下一个 API 密钥"""
    global LAST_KEY_INDEX
    LAST_KEY_INDEX = (LAST_KEY_INDEX + 1) % len(API_KEYS)
    return API_KEYS[LAST_KEY_INDEX]

def save_to_json(filename, new_content):
    """将内容追加到 JSON 文件"""
    # 初始化数据变量
    data = {"status": "ok", "totalResults": 0, "articles": []}
    
    # 尝试读取已有的数据
    if os.path.exists(filename):
        with open(filename, "r", encoding='utf-8') as f:
            try:
                # 读取已存在的文件数据
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {filename} is empty or corrupted. Starting with new data.")
    
    # 追加新数据
    data['articles'].extend(new_content['articles'])
    data['totalResults'] = len(data['articles'])
    
    # 保存更新后的数据
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Updated and saved to {filename} with total results: {data['totalResults']}.")

def update_top_headline():
    """更新头条新闻"""
    for category in CATEGORIES:
        for country in COUNTRIES_LANGUAGES:
            print(f"Started updating category: {category} country: {country} at: {time.strftime('%A, %d. %B %Y %I:%M:%S %p')}")
            newsapi = NewsApiClient(api_key=get_key())
            top_headlines = newsapi.get_top_headlines(category=category, page_size=100)
            save_to_json(f"data/top-headlines/category/{category}.json", top_headlines)
    print("Top headlines updated.")

def update_everything():
    """更新所有相关新闻"""
    newsapi = NewsApiClient(api_key=get_key())
    for source in SOURCES:
        print(f"Started updating source: {source} at: {time.strftime('%A, %d. %B %Y %I:%M:%S %p')}")
        all_articles = newsapi.get_everything(
            sources=source,
            from_param=(datetime.now() - timedelta(hours=10, minutes=30)).date().isoformat(),
            language='en',
            sort_by='publishedAt',
            page_size=100
        )
        save_to_json(f"data/everything/{source}.json", all_articles)
    print("Everything updated.")

@router.get("/top-headlines/update")
async def update_top_headline_api():
    """API 路由：更新头条新闻"""
    update_top_headline()
    return {"status": "updated"}

@router.get("/everything/update")
async def update_everything_api():
    """API 路由：更新所有相关新闻"""
    update_everything()
    return {"status": "updated"}

@router.get("/top-headlines/{category}")
async def filter_by_category(category: str):
    """根据类别过滤头条新闻"""
    filepath = f"data/top-headlines/category/{category}.json"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Data not found")

    now = datetime.now(timezone.utc)
    past_day = now - timedelta(days=2)

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

@router.get("/top-headlines/{category}/filter-by-time")
async def filter_by_time(category: str, start_time: str = Query(...), end_time: str = Query(...)):
    """根据时间过滤头条新闻"""
    filepath = f"data/top-headlines/category/{category}.json"
    try:
        start_dt = datetime.fromisoformat(start_time).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid time format")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Data not found")

    filtered_news = []
    for news in data.get('articles', []):
        pub_time = news.get('publishedAt')
        if not pub_time:
            continue
        try:
            pub_time_obj = datetime.fromisoformat(pub_time.replace("Z", "+00:00"))
        except Exception:
            continue
        if start_dt <= pub_time_obj <= end_dt:
            filtered_news.append(news)

    return {"totalResults": len(filtered_news), "articles": filtered_news}


@router.get("/top-headlines/filter-all-by-time")
async def filter_all_by_time(start_time: str = Query(...), end_time: str = Query(...)):
    """根据时间过滤所有头条新闻"""
    try:
        start_dt = datetime.fromisoformat(start_time).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid time format")

    filtered_news = []
    for category in CATEGORIES:
        filepath = f"data/top-headlines/category/{category}.json"
        print(f"Trying to open: {filepath}")  # Debugging line
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"Loaded {len(data.get('articles', []))} articles from {filepath}")  # Debugging line
        except FileNotFoundError:
            print(f"File does not exist: {filepath}")  # Debugging line
            continue

        for news in data.get("articles", []):
            pub_time_str = news.get("publishedAt")
            if not pub_time_str:
                continue
            try:
                pub_time = datetime.fromisoformat(pub_time_str.replace("Z", "+00:00"))
            except Exception:
                continue
            
            if start_dt <= pub_time <= end_dt:
                filtered_news.append(news)

    return {"totalResults": len(filtered_news), "articles": filtered_news}
    """根据时间过滤所有头条新闻"""
    try:
        start_dt = datetime.fromisoformat(start_time).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid time format")

    filtered_news = []
    for category in CATEGORIES:
        filepath = f"data/top-headlines/category/{category}.json"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            continue
        for news in data.get("articles", []):
            pub_time_str = news.get("publishedAt")
            if not pub_time_str:
                continue
            try:
                pub_time = datetime.fromisoformat(pub_time_str.replace("Z", "+00:00"))
            except Exception:
                continue
            if start_dt <= pub_time <= end_dt:
                filtered_news.append(news)

    return {"totalResults": len(filtered_news), "articles": filtered_news}

@router.get("/everything/{source}")
async def get_everything(source: str):
    """获取特定来源的所有文章"""
    filepath = f"data/everything/{source}.json"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Data not found")

# Scheduler setup
scheduler = BackgroundScheduler()
#INTERVAL = 1  # 每分钟运行一次
#cheduler.add_job(func=update_top_headline, trigger="interval", minutes=INTERVAL)
#cheduler.add_job(func=update_everything, trigger="interval", minutes=INTERVAL)
#每日五点更新：

if not scheduler.running:
    scheduler.start()

atexit.register(lambda: scheduler.shutdown())
print("Scheduler started.")
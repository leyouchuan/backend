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
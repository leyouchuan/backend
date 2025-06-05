import base64, requests, json, os, ast
from dotenv import load_dotenv
from random import randrange
from newsapi import NewsApiClient
import atexit
import time
from flask import Flask, redirect,jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta,timezone


COUNTRIES_LANGUAGES = {"in": "en", "us": "en", "au": "en", "ru": "ru", "fr": "fr", "gb": "en","cn":"zh"}
CATEGORIES = ["business", "entertainment", "general", "health", "science", "sports", "technology"]
SOURCES = ["bbc.co.uk", "cnn.com", "foxnews.com", "google.com"]

app = Flask(__name__)

load_dotenv()

#GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN")
API_KEYS = ast.literal_eval(os.getenv("API_KEYS"))
LAST_KEY_INDEX = randrange(0, len(API_KEYS))


def get_key():
    global LAST_KEY_INDEX
    LAST_KEY_INDEX = (LAST_KEY_INDEX + 1) % len(API_KEYS)
    return API_KEYS[LAST_KEY_INDEX]


def save_to_json(filename, content):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w",encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)
    print("Saved to {0}".format(filename))


@app.route('/')


def update_top_headline():
    for category in CATEGORIES:
        for country in COUNTRIES_LANGUAGES:
            print("Started category:{0} country:{1} at :{2}".format(category, country,
                                                                    time.strftime("%A, %d. %B %Y %I:%M:%S %p")))
            newsapi = NewsApiClient(api_key=get_key())
            top_headlines = newsapi.get_top_headlines(category=category, page_size=10)
            save_to_json(f"data/top-headlines/category/{category}.json", top_headlines)


def update_everything():
    newsapi = NewsApiClient(api_key=get_key())
    for source in SOURCES:
        print("Started source:{0} : {1}".format(source, time.strftime("%A, %d. %B %Y %I:%M:%S %p")))
        all_articles = newsapi.get_everything(sources=source,
                                              from_param=(datetime.now() - timedelta(days=0, hours=3,
                                                                                     minutes=30)).date().isoformat(),
                                              language='en',
                                              sort_by='publishedAt',
                                              page_size=10)
        save_to_json(f"data/everything/{source}.json", all_articles)

#仅按类别筛选，默认时间区间为过去两天
@app.route('/top-headlines/<category>')
def filter_by_category(category):
    filepath = f"data/top-headlines/category/{category}.json"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": "Data not found"}), 404

    # 获取当前UTC时间
    now = datetime.now(timezone.utc)
    # 过去两天的起始时间
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
        # 过滤只包含过去一天的新闻
        if past_day <= pub_time <= now:
            filtered_news.append(news)

    return jsonify({"totalResults": len(filtered_news), "articles": filtered_news})

#按类别与时间筛选
@app.route('/top-headlines/<category>/filter-by-time')
def filter_by_time(category):
    filepath = f"data/top-headlines/category/{category}.json"
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')

    try:
        start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
        end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
    except Exception:
        return jsonify({"error": "输入时间格式错误"}), 400
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": "Data not found"}), 404
    filtered_news=[]
    for news in data.get('articles',[]):
        pub_time=news.get('publishedAt')
        if not pub_time:
            continue
        try:
            pub_time_obj=datetime.fromisoformat(pub_time.replace("Z", "+00:00"))
        except Exception:
            continue
        if start_time<=pub_time_obj<=end_time:
            filtered_news.append(news)
    return jsonify({"totalResults": len(filtered_news), "articles": filtered_news})

#按时间筛选所有类别
@app.route('/top-headlines/filter-all-by-time')
def filter_all_by_time():
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')

    try:
        start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
        end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
    except Exception:
        return jsonify({"error": "输入时间格式错误"}), 400
    #print(f"start_time: {start_time}, end_time: {end_time}")
    filtered_news = []
    for category in CATEGORIES:
        filepath = f"data/top-headlines/category/{category}.json"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            continue
        #print(f"新闻总数: {len(data.get('articles', []))}")
        for news in data.get("articles", []):
            pub_time_str = news.get("publishedAt")
            if not pub_time_str:
                continue
            try:
                pub_time = datetime.fromisoformat(pub_time_str.replace("Z", "+00:00"))
                #print(f"pub_time: {pub_time}")
            except Exception:
                continue
            if start_time <= pub_time <= end_time:
                filtered_news.append(news)

    return jsonify({"totalResults": len(filtered_news), "articles": filtered_news})

#按源筛选
@app.route('/everything/<source>')
def get_everything(source):
    filepath = f"data/everything/{source}.json"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Data not found"}), 404


scheduler = BackgroundScheduler()
#每日五点更新一次
scheduler.add_job(func=update_top_headline, trigger="cron", hour=5, minute=0)
scheduler.add_job(func=update_everything, trigger="cron", hour=5, minute=0)

if not scheduler.running:
    scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

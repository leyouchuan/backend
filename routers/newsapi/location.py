#根据调用新闻标题，提取出其中的地点信息，并返回其经纬度信息至前端以供渲染实体点。
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import os
import json
import spacy
from spacy.pipeline import EntityRuler
import requests
from pydantic import BaseModel
from routers.newsapi.filters import filter_by_category, filter_by_time, filter_all_by_time
from typing import List, Optional

router = APIRouter()

# 加载英文模型
nlp = spacy.load("en_core_web_sm")

# 添加 EntityRuler 用于自定义地名和简称
ruler = nlp.add_pipe("entity_ruler", before="ner")

patterns = [
    {"label": "GPE", "pattern": "U.S."},
    {"label": "GPE", "pattern": "USA"},
    {"label": "GPE", "pattern": "United States"},
    {"label": "GPE", "pattern": "Donald Trump"},  # 映射到美国
    {"label": "GPE", "pattern": [{"TEXT": {"REGEX": "U\\.S\\.?"}}]},  # U.S. 和 U.S
    {"label": "NORP", "pattern": "European"},
    # 你可以根据需要再添加更多模式
]
ruler.add_patterns(patterns)

BAIDU_MAP_AK = "Nz5uCMPZeXyI85ETikbMEZ7tSraPlvZi"

def geocode_location(location_name: str):
    """用百度地图API查询地名经纬度"""
    url = "http://api.map.baidu.com/geocoding/v3/"
    params = {
        "address": location_name,
        "output": "json",
        "ak": BAIDU_MAP_AK,
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    if data.get("status") == 0:
        location = data["result"]["location"]
        return {"lat": location["lat"], "lng": location["lng"]}
    return None

# 地名映射字典（后处理用，统一简称或特例）
location_mapping = {
    "Donald Trump": "United States",
    "U.S.": "United States",
    "U.S": "United States",
    "USA": "United States",
    "United States": "United States",
    "美国": "United States",
    "European": "Europe",
    # 其他映射
}

class ArticlesModel(BaseModel):
    articles: list

@router.get("/articles/with-location")
async def get_articles_with_location(
    category: Optional[str] = Query(None, description="新闻分类"),
    start_time: Optional[str] = Query(None, description="开始时间 ISO 格式"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO 格式")
):
    # 根据条件调用对应筛选函数
    if category and start_time and end_time:
        try:
            data = filter_by_time(category, start_time, end_time)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif category:
        try:
            data = filter_by_category(category)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif start_time and end_time:
        try:
            data = filter_all_by_time(start_time, end_time)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail="请求参数不足，需提供category或start_time与end_time")

    articles = data.get("articles", [])

    # 给每篇文章添加 location 字段
    articles_with_location = []

    for article in articles:
        title = article.get("title", "")
        description = article.get("description", "")
        combined_text = f"{title} {description}".strip()
        if not combined_text:
            continue

        doc = nlp(combined_text)
        loc_texts = set()
        for ent in doc.ents:
            if ent.label_ in {"GPE", "NORP"}:
                loc_texts.add(ent.text)

    # 地点归一化
        normalized_locs = set(location_mapping.get(loc, loc) for loc in loc_texts)

        loc_infos = []
        for loc in normalized_locs:
            coords = geocode_location(loc)
            if coords:
                loc_infos.append({"location": loc, **coords})

        if loc_infos:
            article["location"] = loc_infos
            articles_with_location.append(article)

    # 返回过滤后带location的文章集
    return JSONResponse(content={"totalResults": len(articles_with_location), "articles": articles_with_location})
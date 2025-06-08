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
import ast

router = APIRouter()

@router.get("/articles/with-location")
async def get_articles_with_location(
    category: Optional[str] = Query(None, description="新闻分类"),
    start_time: Optional[str] = Query(None, description="开始时间 ISO 格式"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO 格式")
):
    # 先获取筛选结果
    if category and start_time and end_time:
        try:
            data = await filter_by_time(category, start_time, end_time)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif category:
        try:
            data = await filter_by_category(category)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif start_time and end_time:
        try:
            data = await filter_all_by_time(start_time, end_time)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail="请求参数不足，需提供category或start_time与end_time")

    articles = data.get("articles", [])

    # 只保留带有location字段的文章（说明之前已识别并赋值）
    articles_with_location = [article for article in articles if "location" in article and article["location"]]

    return JSONResponse(content={"totalResults": len(articles_with_location), "articles": articles_with_location})
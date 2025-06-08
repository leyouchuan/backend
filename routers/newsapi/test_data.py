import json
import os
from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

router = APIRouter()

# 数据模型（如果需要）
class NewsResponse(BaseModel):
    # 根据你的json数据结构定义相应的字段
    pass

@router.get("/category/{category}")
async def get_test_data(category: str):
    """获取测试数据"""
    try:
        file_path = f"data/top-headlines/category/{category}.json"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Category {category} not found")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories")
async def get_available_categories():
    """获取所有可用的新闻类别"""
    try:
        categories_dir = "data/top-headlines/category"
        categories = [f.split('.')[0] for f in os.listdir(categories_dir) 
                     if f.endswith('.json') and not f.endswith('.sample')]
        return list(set(categories))  # 去重
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
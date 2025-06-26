import json
import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import geopandas as gpd
from shapely.geometry import Point

router = APIRouter()

# --------------------- 数据模型 ---------------------

class Location(BaseModel):
    location: str
    lat: float
    lng: float

class Source(BaseModel):
    id: Optional[str]
    name: str

class NewsItem(BaseModel):
    source: Source
    author: Optional[str]
    title: str
    description: Optional[str]
    url: str
    urlToImage: Optional[str]
    publishedAt: str
    content: Optional[str]
    location: List[Location] = Field(default_factory=list)

# --------------------- 加载国家边界 ---------------------

def load_country_shapes(data_dir: str = "charts_data") -> gpd.GeoDataFrame:
    """加载国家行政区划shp数据"""
    try:
        countries_file = os.path.join(data_dir, "countries.shp")
        if not os.path.exists(countries_file):
            raise FileNotFoundError(f"国家shp文件不存在: {countries_file}")
        
        gdf = gpd.read_file(countries_file)
        
        # 转为 WGS84 坐标系
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        else:
            gdf = gdf.to_crs(epsg=4326)
        
        return gdf
    except Exception as e:
        print(f"加载国家shp数据时出错: {e}")
        raise

# --------------------- 读取新闻数据 ---------------------

def load_news_from_folder(folder_path: str = "data/top-headlines/category/") -> List[NewsItem]:
    """从指定文件夹读取 JSON 文件中的新闻数据"""
    news_items = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    raw_json = json.load(f)
                    articles = raw_json.get("articles", [])
                    for item in articles:
                        item.setdefault("location", [])
                        item.setdefault("source", {"id": None, "name": "Unknown"})
                        item.setdefault("title", "")
                        item.setdefault("url", "")
                        item.setdefault("publishedAt", "")
                        news_items.append(NewsItem(**item))
                except Exception as e:
                    print(f"[错误] 解析文件 {filename} 失败: {e}")
    
    return news_items

# --------------------- 统计国家新闻数量 ---------------------

def count_news_by_country(news_items: List[NewsItem], countries_gdf: gpd.GeoDataFrame) -> Dict[str, int]:
    """根据经纬度统计每个国家的新闻数量"""
    country_counts = {}

    for news in news_items:
        for loc in news.location:
            point = Point(loc.lng, loc.lat)
            country_match = countries_gdf[countries_gdf.contains(point)]
            if not country_match.empty:
                country_name = country_match.iloc[0].get("NAME", country_match.iloc[0].get("COUNTRY", "未知国家"))
                country_counts[country_name] = country_counts.get(country_name, 0) + 1

    return country_counts

# --------------------- 生成 ECharts 图表配置 ---------------------

def generate_echarts_bar_chart(counts: Dict[str, int]) -> Dict[str, Any]:
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    countries = [item[0] for item in sorted_counts]
    values = [item[1] for item in sorted_counts]

    option = {
        "title": {
            "text": "新闻数量按国家分布",
            "left": "center"
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {
                "type": "shadow"
            }
        },
        "toolbox": {
            "show": True,
            "feature": {
                "saveAsImage": {}
            }
        },
        "xAxis": {
            "type": "category",
            "data": countries,
            "axisLabel": {
                "rotate": 45,
                "interval": 0,
                "fontSize": 10
            }
        },
        "yAxis": {
            "type": "value"
        },
        "series": [{
            "name": "新闻数量",
            "type": "bar",
            "data": values,
            "itemStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 1, "y2": 0,
                    "colorStops": [
                        {"offset": 0, "color": "#19d4ae"},
                        {"offset": 1, "color": "#0ac28d"}
                    ],
                    "global": False
                }
            },
            "label": {
                "show": True,
                "position": "top"
            }
        }]
    }

    return option

# --------------------- API 路由 ---------------------

@router.get("/news-by-country", response_model=Dict[str, Any])
async def get_news_by_country_chart():
    """从本地 JSON 文件读取新闻并生成按国家分布图表"""
    try:
        countries_gdf = load_country_shapes()
        news_items = load_news_from_folder()
        country_counts = count_news_by_country(news_items, countries_gdf)
        chart_data = generate_echarts_bar_chart(country_counts)
        return chart_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成图表时出错: {str(e)}")

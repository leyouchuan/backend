#使用echarts库，绘制查询范围内的新闻数据统计图表
import json
import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

# 设置中文字体支持
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

app = FastAPI(title="新闻地理统计图表API")

# 数据模型
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

# 加载国家行政区划数据
def load_country_shapes(data_dir: str = "charts_data") -> gpd.GeoDataFrame:
    """加载国家行政区划shp数据"""
    try:
        countries_file = os.path.join(data_dir, "countries.shp")
        if not os.path.exists(countries_file):
            raise FileNotFoundError(f"国家shp文件不存在: {countries_file}")
        
        gdf = gpd.read_file(countries_file)
        
        # 确保使用WGS 84坐标系
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)  # 设置缺失的CRS
        else:
            gdf = gdf.to_crs(epsg=4326)  # 转换为WGS 84坐标系
        
        return gdf
    except Exception as e:
        print(f"加载国家shp数据时出错: {e}")
        raise

# 按国家统计新闻数量
def count_news_by_country(news_items: List[NewsItem], countries_gdf: gpd.GeoDataFrame) -> Dict[str, int]:
    """根据经纬度统计每个国家的新闻数量"""
    country_counts = {}
    
    for news in news_items:
        # 检查每条新闻的所有位置
        for loc in news.location:
            point = Point(loc.lng, loc.lat)  # GeoPandas使用(lng, lat)顺序
            
            # 查找该点位于哪个国家
            country_match = countries_gdf[countries_gdf.contains(point)]
            
            if not country_match.empty:
                # 获取国家名称
                country_name = country_match.iloc[0].get('NAME', 
                                                      country_match.iloc[0].get('COUNTRY', '未知国家'))
                # 增加计数
                country_counts[country_name] = country_counts.get(country_name, 0) + 1
    
    return country_counts

def generate_echarts_bar_chart(counts: Dict[str, int]) -> Dict[str, Any]:
    """生成ECharts柱状图数据"""
    # 按新闻数量排序
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    countries = [item[0] for item in sorted_counts]
    values = [item[1] for item in sorted_counts]
    
    # 创建ECharts配置
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
                    "x": 0,
                    "y": 0,
                    "x2": 1,
                    "y2": 0,
                    "colorStops": [
                        {"offset": 0, "color": '#19d4ae'},  
                        {"offset": 1, "color": '#0ac28d'}  
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

# API端点
@app.post("/news-by-country", response_model=Dict[str, Any])
async def get_news_by_country_chart(news_items: List[NewsItem]):
    """获取按国家统计的新闻数量图表"""
    try:
        # 加载国家shp数据
        countries_gdf = load_country_shapes()
        
        # 统计新闻数量
        country_counts = count_news_by_country(news_items, countries_gdf)
        
        # 生成ECharts图表数据
        chart_data = generate_echarts_bar_chart(country_counts)
        
        return chart_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成图表时出错: {str(e)}")

#将当前视野地图导出为图片，点数据采用geojson格式。
import io
import base64
import folium
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import tempfile
import os
import time

router = APIRouter()

from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ExportMapResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    message: str
    geojson: Optional[Dict[str, Any]] = None

class Source(BaseModel):
    id: Optional[str]
    name: Optional[str]

class LocationItem(BaseModel):
    location: Optional[str] = None
    lat: float
    lng: float

class Article(BaseModel):
    id: int
    source: Source
    author: Optional[str] = None
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    urlToImage: Optional[str] = None
    publishedAt: Optional[str] = None
    content: Optional[str] = None
    location: List[LocationItem]

class ExportMapRequest(BaseModel):
    center_lat: float
    center_lng: float
    zoom: int
    width: int = 1024
    height: int = 768
    articles: List[Article]  # 替换 points
    basemap_type: str = "OpenStreetMap"

def create_folium_map(request: ExportMapRequest) -> folium.Map:
    tiles_mapping = {
        # 保持不变
    }
    tiles = tiles_mapping.get(request.basemap_type, "OpenStreetMap")

    m = folium.Map(
        location=[request.center_lat, request.center_lng],
        zoom_start=request.zoom,
        tiles=tiles,
        width=request.width,
        height=request.height
    )

    for article in request.articles:
        # 逐个article对应多个点
        for loc in article.location:
            popup_text = f"<b>{article.title}</b><br>"
            popup_text += (article.description or "") + "<br>"
            popup_text += f"来源: {article.source.name if article.source else ''}<br>"
            popup_text += f"发布时间: {article.publishedAt or ''}<br>"
            if article.url:
                popup_text += f"<a href='{article.url}' target='_blank'>阅读全文</a>"

            folium.Marker(
                location=[loc.lat, loc.lng],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=article.title
            ).add_to(m)

    return m

#转json
def articles_to_geojson(articles: List[Article]) -> Dict[str, Any]:
    features = []
    for article in articles:
        for loc in article.location:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [loc.lng, loc.lat]
                },
                "properties": {
                    "id": article.id,
                    "title": article.title,
                    "description": article.description,
                    "url": article.url,
                    "source": article.source.dict() if article.source else {},
                    "publishedAt": article.publishedAt
                }
            })
    return {
        "type": "FeatureCollection",
        "features": features
    }

def capture_map_image(folium_map: folium.Map, width: int, height: int) -> str:
    """使用undetected_chromedriver截取地图图片并返回base64编码"""
    import undetected_chromedriver as uc
    
    driver = None
    temp_file = None
    
    try:
        # 使用undetected_chromedriver自动匹配Chrome版本
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--window-size={width},{height}")
        
        driver = uc.Chrome(options=options)
        
        # 设置窗口大小
        driver.set_window_size(width, height)
        
        # 保存folium地图为临时HTML文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            temp_file = f.name
            folium_map.save(f.name)
        
        # 加载HTML文件
        driver.get(f"file://{temp_file}")
        
        # 等待地图加载完成
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "leaflet-container")))
        
        # 额外等待确保瓦片加载完成
        time.sleep(3)
        
        # 截图
        screenshot = driver.get_screenshot_as_png()
        
        # 转换为PIL Image并调整大小
        image = Image.open(io.BytesIO(screenshot))
        if image.size != (width, height):
            try:
                image = image.resize((width, height), Image.Resampling.LANCZOS)
            except AttributeError:
                image = image.resize((width, height), Image.LANCZOS)
        
          # 转换为base64之前，先保存图片到本地
        image = Image.open(io.BytesIO(screenshot))
        if image.size != (width, height):
            try:
                image = image.resize((width, height), Image.Resampling.LANCZOS)
            except AttributeError:
                image = image.resize((width, height), Image.LANCZOS)
        
        # 保存图片到本地
        output_path = "test_output.png"  # 图片将保存在项目根目录
        image.save(output_path)
        print(f"图片已保存到: {output_path}")
        
        # 转换为base64
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        return img_base64
        
    except Exception as e:
        import traceback
        error_details = str(e) + "\n" + traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"截图失败: {error_details}")
    
    finally:
        # 清理资源
        if driver:
            driver.quit()
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)

@router.post("/export", response_model=ExportMapResponse)
async def export_map(request: ExportMapRequest):
    try:
        # 参数验证
        if not (-90 <= request.center_lat <= 90):
            raise HTTPException(status_code=400, detail="纬度必须在-90到90之间")
        
        if not (-180 <= request.center_lng <= 180):
            raise HTTPException(status_code=400, detail="经度必须在-180到180之间")
        
        if not (1 <= request.zoom <= 18):
            raise HTTPException(status_code=400, detail="缩放级别必须在1到18之间")
        
        if request.width <= 0 or request.height <= 0:
            raise HTTPException(status_code=400, detail="图片尺寸必须大于0")
        
        # 创建folium地图
        folium_map = create_folium_map(request)
        image_base64 = capture_map_image(folium_map, request.width, request.height)
        geojson_data = articles_to_geojson(request.articles)

        return ExportMapResponse(
            success=True,
            image_base64=image_base64,
            message=f"成功导出地图，包含{len(request.articles)}条新闻",
            geojson=geojson_data )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出地图失败: {str(e)}")
    

#这些用不到。。。
@router.get("/export/test")
async def test_export():
    """
    测试接口，导出一个示例地图
    """
    # 示例数据
    test_request = ExportMapRequest(
        center_lat=39.9042,  # 北京
        center_lng=116.4074,
        zoom=10,
        width=800,
        height=600,
        points=[
            PointData(latitude=39.9042, longitude=116.4074, properties={"name": "天安门", "type": "景点"}),
            PointData(latitude=39.9163, longitude=116.3972, properties={"name": "故宫", "type": "景点"}),
            PointData(latitude=39.8828, longitude=116.4447, properties={"name": "天坛", "type": "景点"})
        ],
        basemap_type="OpenStreetMap"
    )
    
    return await export_map(test_request)

@router.get("/basemap-types")
async def get_basemap_types():
    """
    获取支持的底图类型列表
    """
    return {
        "basemap_types": [
            {"name": "OpenStreetMap", "title": "开放街道地图"},
            {"name": "Stamen Terrain", "title": "地形图"},
            {"name": "Stamen Toner", "title": "黑白地图"},
            {"name": "CartoDB positron", "title": "CartoDB明亮"},
            {"name": "CartoDB dark_matter", "title": "CartoDB暗色"}
        ]
    }

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

class PointData(BaseModel):
    """点数据模型"""
    latitude: float
    longitude: float
    properties: Optional[Dict[str, Any]] = {}

class ExportMapRequest(BaseModel):
    """地图导出请求模型"""
    center_lat: float
    center_lng: float
    zoom: int
    width: int = 1024
    height: int = 768
    points: Optional[List[PointData]] = []
    basemap_type: str = "OpenStreetMap"  # 可选: OpenStreetMap, Stamen Terrain, CartoDB positron等

class ExportMapResponse(BaseModel):
    """地图导出响应模型"""
    success: bool
    image_base64: Optional[str] = None
    message: str
    geojson: Optional[Dict[str, Any]] = None

def create_folium_map(request: ExportMapRequest) -> folium.Map:
    """创建folium地图对象"""
    # 根据basemap_type选择底图
    tiles_mapping = {
        "OpenStreetMap": "OpenStreetMap",
        "Stamen Terrain": "Stamen Terrain",
        "Stamen Toner": "Stamen Toner",
        "CartoDB positron": "CartoDB positron",
        "CartoDB dark_matter": "CartoDB dark_matter"
    }
    
    tiles = tiles_mapping.get(request.basemap_type, "OpenStreetMap")
    
    # 创建地图
    m = folium.Map(
        location=[request.center_lat, request.center_lng],
        zoom_start=request.zoom,
        tiles=tiles,
        width=request.width,
        height=request.height
    )
    
    # 添加点数据
    if request.points:
        for point in request.points:
            # 创建标记
            popup_text = ""
            if point.properties:
                popup_text = "<br>".join([f"{k}: {v}" for k, v in point.properties.items()])
            
            folium.Marker(
                location=[point.latitude, point.longitude],
                popup=folium.Popup(popup_text, max_width=300) if popup_text else None,
                tooltip=f"点位: ({point.latitude:.6f}, {point.longitude:.6f})"
            ).add_to(m)
    
    return m

def points_to_geojson(points: List[PointData]) -> Dict[str, Any]:
    """将点数据转换为GeoJSON格式"""
    features = []
    
    for point in points:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [point.longitude, point.latitude]
            },
            "properties": point.properties or {}
        }
        features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return geojson

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
    """
    导出当前视野的地图为图片
    
    参数说明:
    - center_lat: 地图中心纬度
    - center_lng: 地图中心经度
    - zoom: 缩放级别 (1-18)
    - width: 图片宽度 (默认1024)
    - height: 图片高度 (默认768)
    - points: 点数据列表
    - basemap_type: 底图类型
    
    返回:
    - success: 是否成功
    - image_base64: 图片的base64编码
    - message: 响应消息
    - geojson: 点数据的GeoJSON格式
    """
    
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
        
        # 截取地图图片
        image_base64 = capture_map_image(folium_map, request.width, request.height)
        
        # 转换点数据为GeoJSON
        geojson_data = None
        if request.points:
            geojson_data = points_to_geojson(request.points)
        
        return ExportMapResponse(
            success=True,
            image_base64=image_base64,
            message=f"成功导出地图图片，包含{len(request.points or [])}个点",
            geojson=geojson_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出地图失败: {str(e)}")

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

#示例，如果导出图片用到geoserver或是数据存储用到数据库，这个接口就不必要。
import requests
from fastapi import APIRouter, HTTPException
router = APIRouter()

GEOSERVER_URL = "http://localhost:8080/geoserver/rest/"
GEOSERVER_USER = "admin"
GEOSERVER_PASS = "geoserver"


basemap_configs = [
    {
        "name": "low_res",
        "title": "低分辨率全球底图",
        "workspace": "global",
        "layer_name": "low_res_layer",
        "min_zoom": 0,
        "max_zoom": 8,
        "service_url": f"{GEOSERVER_URL}gwc/service/wmts"
    },
    {
        "name": "mid_res",
        "title": "中分辨率全球底图",
        "workspace": "global",
        "layer_name": "mid_res_layer",
        "min_zoom": 9,
        "max_zoom": 14,
        "service_url": f"{GEOSERVER_URL}gwc/service/wmts"
    },
    {
        "name": "high_res",
        "title": "高分辨率全球底图",
        "workspace": "global",
        "layer_name": "high_res_layer",
        "min_zoom": 15,
        "max_zoom": 18,
        "service_url": f"{GEOSERVER_URL}gwc/service/wmts"
    },
]

@router.get("/basemaps")
async def get_basemaps():
    """
    返回多底图图层配置，供前端根据缩放级别选择
    """
    return basemap_configs


@router.get("/layers")
async def get_layers():
    """
    从GeoServer REST API获取所有图层信息
    """
    url = f"{GEOSERVER_URL}layers.json"
    resp = requests.get(url, auth=(GEOSERVER_USER, GEOSERVER_PASS))
    if resp.status_code == 200:
        return resp.json()
    else:
        raise HTTPException(status_code=resp.status_code, detail="获取GeoServer图层失败")

from dotenv import load_dotenv
load_dotenv()


from fastapi import FastAPI
import uvicorn
from routers.newsapi.api import router
from routers.newsapi.location import router as location_router
from routers.geoserver.exportMap import router as export_router
from routers.geoserver.layers import router as layers_router
from routers.newsapi.charts import router as charts_router
from fastapi.middleware.cors import CORSMiddleware
from routers.newsapi.api import setup_scheduler
from routers.newsapi import test_data
import os

#这一段不要
#raw_keys = os.getenv("geocoding_api_key")
#print("读取到的 geocoding_api_key =", raw_keys)
#API_KEYS = raw_keys.split(",") if raw_keys else []
#print("解析后的 API_KEYS =", API_KEYS)
HOST= os.getenv("host", "127.0.0.1")
PORT= os.getenv("port", 7000)

app = FastAPI()

#跨域请求设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

from fastapi.staticfiles import StaticFiles
import os
app.mount("/data", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "data")), name="data")

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

# 包含新闻路由
app.include_router(router, prefix="/news")
# 包含地点提取路由
app.include_router(location_router, prefix="/news/locations")
# 图表路由
app.include_router(charts_router, prefix="/news/charts")

app.include_router(test_data.router, prefix="/news/test")  # 新增测试数据路由

app.include_router(export_router, prefix="/map", tags=["地图导出"])
app.include_router(layers_router, prefix="/geoserver", tags=["图层管理"])

# 设置自动更新

@app.on_event("startup")
async def startup_event():
    setup_scheduler()

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)

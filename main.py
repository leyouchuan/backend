from fastapi import FastAPI
import uvicorn
from routers.newsapi.api import router
from routers.newsapi.location import router as location_router
from routers.geoserver.exportMap import router as export_router
from routers.geoserver.layers import router as layers_router
from db import database

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

# 包含新闻路由
app.include_router(router, prefix="/news")
# 包含地点提取路由
app.include_router(location_router, prefix="/news/locations")

app.include_router(export_router, prefix="/map", tags=["地图导出"])
app.include_router(layers_router, prefix="/geoserver", tags=["图层管理"])

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
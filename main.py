from fastapi import FastAPI
import uvicorn
from routers.newsapi.api import router
from routers.newsapi.location import router as location_router

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

# 包含新闻路由
app.include_router(router, prefix="/news")
# 包含地点提取路由
app.include_router(location_router, prefix="/news/locations")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
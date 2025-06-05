from fastapi import FastAPI
import uvicorn
from routers.newsapi.api import router

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

# 包含新闻路由
app.include_router(router, prefix="/news")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
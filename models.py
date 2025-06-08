from sqlalchemy import (
    MetaData, Table, Column, Integer, String, Text, DateTime, ForeignKey, Double
)

metadata = MetaData()

# 定义 articles 表
articles = Table(
    "articles", metadata,
    Column("id", Integer, primary_key=True),
    Column("source_id", String),
    Column("source_name", String),
    Column("author", String),
    Column("title", Text, nullable=False),
    Column("description", Text),
    Column("url", Text, nullable=False, unique=True),
    Column("url_to_image", Text),
    Column("published_at", DateTime(timezone=True), nullable=False),
    Column("content", Text),
    Column("category", String),
    Column("country", String),
)

# 定义 article_locations 表
article_locations = Table(
    "article_locations", metadata,
    Column("id", Integer, primary_key=True),
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE")),
    Column("location_name", String, nullable=False),
    Column("lat", Double, nullable=False),
    Column("lng", Double, nullable=False),
)
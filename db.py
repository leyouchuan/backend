# db.py
from databases import Database

DATABASE_URL = "postgresql+asyncpg://postgres:0plm9okn@localhost:5432/News"
database = Database(DATABASE_URL)
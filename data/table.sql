CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR NULL,
    source_name VARCHAR NULL,
    author VARCHAR NULL,
    title TEXT NOT NULL,
    description TEXT NULL,
    url TEXT UNIQUE NOT NULL,
    url_to_image TEXT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    content TEXT NULL,
    category VARCHAR NULL,
    country VARCHAR NULL
);

CREATE TABLE article_locations (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    location_name VARCHAR NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL
);
import spacy
import requests
import os
import ast
import json
import requests
import time
from random import randrange
from fuzzywuzzy import process

nlp = spacy.load("en_core_web_sm")
ruler = nlp.add_pipe("entity_ruler", before="ner")
patterns = [
    {"label": "GPE", "pattern": "U.S."},
    {"label": "GPE", "pattern": "USA"},
    {"label": "GPE", "pattern": "United States"},
    {"label": "NORP", "pattern": "European"},
]
ruler.add_patterns(patterns)

BAIDU_MAP_AK = ast.literal_eval(os.getenv("geocoding_api_key"))
LAST_KEY_INDEX = randrange(0, len(BAIDU_MAP_AK))
def get_key():
    """获取下一个 API 密钥"""
    global LAST_KEY_INDEX
    LAST_KEY_INDEX = (LAST_KEY_INDEX + 1) % len(BAIDU_MAP_AK)
    return BAIDU_MAP_AK[LAST_KEY_INDEX]

#表1
manual_coords_mapping='data/manual_coords_mapping.json'
try:
    with open(manual_coords_mapping, 'r', encoding='utf-8') as f:
        manual_coords_mapping = json.load(f)
except Exception as e:
    print(f"加载手动经纬度映射文件失败: {e}")
    manual_coords_mapping = {}  
#表2
mapping_file = 'data\location_mapping.json'
try:
    with open(mapping_file, 'r', encoding='utf-8') as f:
        location_mapping = json.load(f)
except Exception as e:
    print(f"加载映射文件失败: {e}")
    location_mapping = {}
all_reference_names = list(location_mapping.keys())

def smart_map_location(raw_location_name):
    if raw_location_name in location_mapping:
        return location_mapping[raw_location_name]

    best_match, score = process.extractOne(raw_location_name, all_reference_names)
    if score >= 80:
        return location_mapping[best_match]

    print(f"警告: 地名 '{raw_location_name}' 未匹配，建议加入映射表")
    return raw_location_name

def geocode_location(location_name: str):
    if location_name in manual_coords_mapping:
        print(f"使用手动经纬度: {location_name}")
        return manual_coords_mapping[location_name]
    
    url = "http://api.map.baidu.com/geocoding/v3/"
    params = {
        "address": location_name,
        "output": "json",
        "ak": get_key(),
    }
    print(f"Geocoding location: {location_name}")
    time.sleep(1)
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if data.get("status") == 0:
            loc = data["result"]["location"]
            return {"lat": loc["lat"], "lng": loc["lng"]}
        else:
            print(f"百度地图API返回错误状态: {data.get('msg', '无错误信息')}")
    except Exception as e:
        print(f"请求错误: {e}")
    return None

def add_location_info(articles):
    new_articles = []
    for article in articles:
        title = article.get("title", "")
        description = article.get("description", "")
        combined_text = f"{title} {description}".strip()
        if not combined_text:
            continue

        doc = nlp(combined_text)
        loc_texts = set(ent.text for ent in doc.ents if ent.label_ in {"GPE", "NORP"})

        normalized_locs = set(location_mapping.get(loc, loc) for loc in loc_texts)

        loc_infos = []
        for loc in normalized_locs:
            coords = geocode_location(loc)
            if coords:
                loc_infos.append({"location": loc, **coords})

        if loc_infos:
            article["location"] = loc_infos
            new_articles.append(article)

    return new_articles
import os
import json
import spacy
import requests
import ast
import time
from random import randrange
from fuzzywuzzy import process

nlp = spacy.load("en_core_web_sm")

BAIDU_MAP_AK = ast.literal_eval(os.getenv("geocoding_api_key"))
LAST_KEY_INDEX = randrange(0, len(BAIDU_MAP_AK))


def get_key():
    global LAST_KEY_INDEX
    LAST_KEY_INDEX = (LAST_KEY_INDEX + 1) % len(BAIDU_MAP_AK)
    return BAIDU_MAP_AK[LAST_KEY_INDEX]

manual_coords_mapping='data/manual_coords_mapping.json'
try:
    with open(manual_coords_mapping, 'r', encoding='utf-8') as f:
        manual_coords_mapping = json.load(f)
except Exception as e:
    print(f"加载手动经纬度映射文件失败: {e}")
    manual_coords_mapping = {}  
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


def add_location_info_to_articles(articles):
    new_articles = []
    for article in articles:
        if "location" in article and article["location"]:
            new_articles.append(article)
            continue

        combined_text = f"{article.get('title', '')} {article.get('description', '')}".strip()
        if not combined_text:
            continue

        doc = nlp(combined_text)
        loc_texts = set(ent.text for ent in doc.ents if ent.label_ in {"GPE", "NORP"})

        normalized_locs = set()
        for loc in loc_texts:
            mapped_loc = smart_map_location(loc)
            if mapped_loc:
                normalized_locs.add(mapped_loc)

        loc_infos = []
        for loc in normalized_locs:
            coords = geocode_location(loc)
            if coords:
                loc_infos.append({"location": loc, **coords})

        if loc_infos:
            article["location"] = loc_infos
            new_articles.append(article)

    return new_articles


def process_file(filepath):
    print(f"开始处理文件: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return

    articles = data.get("articles", [])
    updated_articles = add_location_info_to_articles(articles)

    if not updated_articles:
        print(f"{filepath} 中无有效地理信息，跳过保存。")
        return

    data["articles"] = updated_articles
    data["totalResults"] = len(updated_articles)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"更新完成，保存了 {len(updated_articles)} 篇文章\n")
    except Exception as e:
        print(f"保存文件出错: {e}")


def batch_process_path(path):
    if os.path.isfile(path):
        if path.endswith(".json"):
            process_file(path)
        else:
            print(f"跳过非JSON文件: {path}")
    elif os.path.isdir(path):
        print(f"开始递归处理目录: {path}")
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".json"):
                    process_file(os.path.join(root, file))
    else:
        print(f"路径不存在: {path}")


if __name__ == "__main__":
    data_path = r"data\top-headlines\category\business.json"
    print(f"启动数据处理，目标路径: {data_path}\n")
    batch_process_path(data_path)
    print("所有任务完成。")
import os
from dotenv import load_dotenv

# 强制指定 .env 文件路径（确保路径无误）
dotenv_path = "/var/www/ednews/.env"
load_dotenv(dotenv_path=dotenv_path)

# 打印环境变量
print("🧪 os.getcwd() =", os.getcwd())
print("🧪 geocoding_api_key (raw) =", os.getenv("geocoding_api_key"))

# 分割字符串
raw_keys = os.getenv("geocoding_api_key")
if raw_keys is None:
    print("❌ 没有获取到 geocoding_api_key")
else:
    keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
    print("✅ 解析后的 keys =", keys)

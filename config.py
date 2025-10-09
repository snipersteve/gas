import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot配置
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# API配置
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', 'YourApiKeyToken')
ETHERSCAN_API_BASE_URL = "https://api.etherscan.io/v2/api"

# BSC链ID
BSC_CHAIN_ID = 56

# 余额阈值 (BNB)
LOW_BALANCE_THRESHOLD = 0.05

# 检查间隔 (分钟)
CHECK_INTERVAL = 30

# 数据存储文件
USER_DATA_FILE = "user_data.json"
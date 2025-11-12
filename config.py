import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot配置
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# API配置
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', 'YourApiKeyToken')
ETHERSCAN_API_BASE_URL = "https://api.bscscan.com/api"  # 使用BSC官方API

# BSC链ID（BscScan API不需要chainid参数）
BSC_CHAIN_ID = None

# 余额阈值 (BNB)
LOW_BALANCE_THRESHOLD = 0.05

# 检查间隔 (分钟)
CHECK_INTERVAL = 30

# API查询间隔 (秒) - 避免触发API限制
API_QUERY_INTERVAL = 3

# 数据存储文件
USER_DATA_FILE = "user_data.json"

# BSC代币合约地址
TOKEN_CONTRACTS = {
    'USDT': '0x55d398326f99059fF775485246999027B3197955',  # BSC-USD (Tether USD)
    'USDC': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d'   # USD Coin
}
import requests
import time
from decimal import Decimal
from config import ETHERSCAN_API_KEY, ETHERSCAN_API_BASE_URL, BSC_CHAIN_ID

class BSCBalanceChecker:
    def __init__(self):
        self.api_key = ETHERSCAN_API_KEY
        self.base_url = ETHERSCAN_API_BASE_URL
        self.chain_id = BSC_CHAIN_ID
    
    def is_valid_address(self, address):
        """验证以太坊地址格式"""
        if not address or len(address) != 42:
            return False
        if not address.startswith('0x'):
            return False
        try:
            int(address[2:], 16)
            return True
        except ValueError:
            return False
    
    def get_bnb_balance(self, address):
        """获取指定地址的BNB余额"""
        if not self.is_valid_address(address):
            raise ValueError(f"Invalid address: {address}")
        
        url = f"{self.base_url}"
        params = {
            'chainid': self.chain_id,
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': 'latest',
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == '1':
                # 将wei转换为BNB (1 BNB = 10^18 wei)
                balance_wei = int(data.get('result', '0'))
                balance_bnb = Decimal(balance_wei) / Decimal(10**18)
                return float(balance_bnb)
            else:
                error_msg = data.get('message', 'Unknown error')
                raise Exception(f"API Error: {error_msg}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
        except ValueError as e:
            raise Exception(f"Invalid response format: {str(e)}")
    
    def check_low_balance(self, address, threshold=0.05):
        """检查地址余额是否低于阈值"""
        try:
            balance = self.get_bnb_balance(address)
            return balance < threshold, balance
        except Exception as e:
            print(f"Error checking balance for {address}: {str(e)}")
            return False, 0.0
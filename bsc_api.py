import aiohttp
import asyncio
import time
from decimal import Decimal
from config import ETHERSCAN_API_KEY, ETHERSCAN_API_BASE_URL, BSC_CHAIN_ID, TOKEN_CONTRACTS

class BSCBalanceChecker:
    def __init__(self):
        self.api_key = ETHERSCAN_API_KEY
        self.base_url = ETHERSCAN_API_BASE_URL
        self.chain_id = BSC_CHAIN_ID
        self.session = None
        # BSC公共RPC节点列表（作为备用）
        self.rpc_urls = [
            "https://bsc-dataseed1.binance.org",
            "https://bsc-dataseed2.binance.org",
            "https://bsc-dataseed3.binance.org",
            "https://bsc-dataseed4.binance.org",
        ]
        self.current_rpc_index = 0
    
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
    
    async def get_session(self):
        """获取或创建aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close_session(self):
        """关闭aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_bnb_balance_via_rpc(self, address):
        """通过RPC节点获取BNB余额（备用方法，无需API密钥）"""
        if not self.is_valid_address(address):
            raise ValueError(f"Invalid address: {address}")

        # 轮询使用不同的RPC节点
        rpc_url = self.rpc_urls[self.current_rpc_index % len(self.rpc_urls)]
        self.current_rpc_index += 1

        # JSON-RPC请求
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [address, "latest"],
            "id": 1
        }

        try:
            session = await self.get_session()
            async with session.post(rpc_url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()

                if 'result' in data:
                    # 结果是十六进制字符串，转换为整数（wei）
                    balance_wei = int(data['result'], 16)
                    balance_bnb = Decimal(balance_wei) / Decimal(10**18)
                    return float(balance_bnb)
                else:
                    error_msg = data.get('error', {}).get('message', 'Unknown RPC error')
                    raise Exception(f"RPC Error: {error_msg}")

        except aiohttp.ClientError as e:
            raise Exception(f"RPC Network error: {str(e)}")
        except (ValueError, KeyError) as e:
            raise Exception(f"RPC response format error: {str(e)}")

    async def get_bnb_balance(self, address):
        """获取指定地址的BNB余额（异步，自动故障转移）"""
        if not self.is_valid_address(address):
            raise ValueError(f"Invalid address: {address}")

        # 优先使用RPC节点（更稳定，无API密钥限制）
        try:
            return await self.get_bnb_balance_via_rpc(address)
        except Exception as rpc_error:
            # RPC失败，尝试使用Etherscan API作为备用
            pass

        # 备用：使用Etherscan API
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
            session = await self.get_session()
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get('status') == '1':
                    # 将wei转换为BNB (1 BNB = 10^18 wei)
                    balance_wei = int(data.get('result', '0'))
                    balance_bnb = Decimal(balance_wei) / Decimal(10**18)
                    return float(balance_bnb)
                else:
                    error_msg = data.get('message', 'Unknown error')
                    raise Exception(f"API Error: {error_msg}")

        except aiohttp.ClientError as e:
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

    async def get_token_balance_via_rpc(self, address, contract_address):
        """通过RPC节点获取ERC20代币余额（备用方法，无需API密钥）"""
        if not self.is_valid_address(address):
            raise ValueError(f"Invalid address: {address}")

        if not self.is_valid_address(contract_address):
            raise ValueError(f"Invalid contract address: {contract_address}")

        # 轮询使用不同的RPC节点
        rpc_url = self.rpc_urls[self.current_rpc_index % len(self.rpc_urls)]
        self.current_rpc_index += 1

        # 构造balanceOf(address)调用
        # balanceOf函数选择器: 0x70a08231
        # 参数: 地址（补齐到32字节）
        address_param = address[2:].lower().zfill(64)  # 去掉0x，补齐到64位
        data = f"0x70a08231{address_param}"

        # JSON-RPC请求 - eth_call调用合约方法
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [
                {
                    "to": contract_address,
                    "data": data
                },
                "latest"
            ],
            "id": 1
        }

        try:
            session = await self.get_session()
            async with session.post(rpc_url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                result = await response.json()

                if 'result' in result:
                    # 结果是十六进制字符串
                    balance_wei = int(result['result'], 16)
                    # USDT和USDC都是18位小数
                    balance = Decimal(balance_wei) / Decimal(10**18)
                    return float(balance)
                else:
                    error_msg = result.get('error', {}).get('message', 'Unknown RPC error')
                    raise Exception(f"RPC Error: {error_msg}")

        except aiohttp.ClientError as e:
            raise Exception(f"RPC Network error: {str(e)}")
        except (ValueError, KeyError) as e:
            raise Exception(f"RPC response format error: {str(e)}")

    async def get_token_balance(self, address, contract_address):
        """获取指定地址的ERC20代币余额（异步，自动故障转移）"""
        if not self.is_valid_address(address):
            raise ValueError(f"Invalid address: {address}")

        if not self.is_valid_address(contract_address):
            raise ValueError(f"Invalid contract address: {contract_address}")

        # 优先使用RPC节点（更稳定，无API密钥限制）
        try:
            return await self.get_token_balance_via_rpc(address, contract_address)
        except Exception as rpc_error:
            # RPC失败，尝试使用Etherscan API作为备用
            pass

        # 备用：使用Etherscan API
        url = f"{self.base_url}"
        params = {
            'module': 'account',
            'action': 'tokenbalance',
            'contractaddress': contract_address,
            'address': address,
            'tag': 'latest',
            'apikey': self.api_key
        }

        # BSC API不需要chainid参数
        if self.chain_id is not None:
            params['chainid'] = self.chain_id

        try:
            session = await self.get_session()
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get('status') == '1':
                    # USDT和USDC都是18位小数
                    balance_raw = int(data.get('result', '0'))
                    balance = Decimal(balance_raw) / Decimal(10**18)
                    return float(balance)
                else:
                    error_msg = data.get('message', 'Unknown error')
                    raise Exception(f"API Error: {error_msg}")

        except aiohttp.ClientError as e:
            raise Exception(f"Network error: {str(e)}")
        except ValueError as e:
            raise Exception(f"Invalid response format: {str(e)}")

    async def get_all_balances(self, address):
        """获取地址的所有余额（BNB、USDT、USDC）（异步）"""
        balances = {
            'BNB': 0.0,
            'USDT': 0.0,
            'USDC': 0.0
        }

        try:
            balances['BNB'] = await self.get_bnb_balance(address)
        except Exception as e:
            print(f"Error getting BNB balance: {str(e)}")

        try:
            balances['USDT'] = await self.get_token_balance(address, TOKEN_CONTRACTS['USDT'])
        except Exception as e:
            print(f"Error getting USDT balance: {str(e)}")

        try:
            balances['USDC'] = await self.get_token_balance(address, TOKEN_CONTRACTS['USDC'])
        except Exception as e:
            print(f"Error getting USDC balance: {str(e)}")

        return balances
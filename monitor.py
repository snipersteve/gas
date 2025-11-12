import asyncio
import time
from bsc_api import BSCBalanceChecker
from user_manager import UserManager
from telegram_bot import GasAlertBot
from config import LOW_BALANCE_THRESHOLD, CHECK_INTERVAL, API_QUERY_INTERVAL

class BalanceMonitor:
    def __init__(self, bot: GasAlertBot):
        self.balance_checker = BSCBalanceChecker()
        self.user_manager = UserManager()
        self.bot = bot
        self.is_running = False
    
    async def query_single_address(self, address: str):
        """查询单个地址的余额（单次尝试）"""
        try:
            balance = await self.balance_checker.get_bnb_balance(address)
            return {'address': address, 'balance': balance, 'success': True, 'error': None}
        except Exception as e:
            return {'address': address, 'balance': 0.0, 'success': False, 'error': str(e)}

    async def query_batch_with_delay(self, addresses, delay_between_requests=0.3):
        """批量查询地址，请求之间有延迟以避免触发API限制"""
        results = []
        for i, address in enumerate(addresses):
            result = await self.query_single_address(address)
            results.append(result)
            # 每个请求后都添加延迟，包括最后一个（0.3秒 = 每秒3.3次，安全余量）
            await asyncio.sleep(delay_between_requests)
        return results

    async def check_all_balances(self):
        """检查所有监控地址的余额 - 使用限速并发查询和重试机制"""
        print(f"⏰ Starting balance check at {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 重新加载用户数据以获取最新的地址列表
        self.user_manager.users_data = self.user_manager.load_data()

        address_to_users = self.user_manager.get_user_addresses_mapping()
        current_time = time.time()

        if not address_to_users:
            print("ℹ️ No addresses to check")
            return

        # 批次重试逻辑：持续重试直到所有地址都成功
        all_addresses = list(address_to_users.keys())
        successful_results = {}  # 存储成功的结果 {address: balance}
        addresses_to_query = all_addresses.copy()
        retry_round = 0
        max_retry_rounds = 10  # 最多重试10轮，避免无限循环

        print(f"🔄 Starting rate-limited query for {len(all_addresses)} addresses...")

        while addresses_to_query and retry_round < max_retry_rounds:
            retry_round += 1

            if retry_round > 1:
                wait_time = min(retry_round * 2, 10)  # 等待2秒、4秒、6秒...最多10秒
                print(f"⏳ Retry round {retry_round}, waiting {wait_time}s before querying {len(addresses_to_query)} failed addresses...")
                await asyncio.sleep(wait_time)

            # 限速查询：请求之间有0.3秒延迟（每秒3.3次）
            results = await self.query_batch_with_delay(addresses_to_query, delay_between_requests=0.3)

            # 分离成功和失败的结果
            failed_addresses = []
            for result in results:
                if result['success']:
                    successful_results[result['address']] = result['balance']
                    if retry_round > 1:
                        print(f"✅ Retry succeeded: {result['address'][:10]}...{result['address'][-8:]} = {result['balance']:.6f} BNB")
                else:
                    failed_addresses.append(result['address'])
                    print(f"⚠️ Query failed for {result['address'][:10]}...{result['address'][-8:]}: {result['error']}")

            addresses_to_query = failed_addresses

        # 统计结果
        total_count = len(all_addresses)
        success_count = len(successful_results)
        failed_count = len(addresses_to_query)

        if failed_count > 0:
            print(f"⚠️ Warning: {failed_count} addresses still failed after {retry_round} rounds")
            for addr in addresses_to_query:
                print(f"   ❌ {addr[:10]}...{addr[-8:]}")

        print(f"📊 Query completed: {success_count}/{total_count} successful")

        # 只处理成功查询的地址
        alerts_sent = 0
        for address, balance in successful_results.items():
            user_ids = address_to_users[address]

            # 为每个用户检查其自定义阈值
            for user_id in user_ids:
                threshold = self.user_manager.get_threshold(user_id)

                if balance < threshold:
                    print(f"🔴 Low balance detected for user {user_id}: {address[:10]}...{address[-8:]} = {balance:.6f} BNB (threshold: {threshold})")

                    if self.user_manager.should_send_alert(user_id, address, current_time):
                        await self.bot.send_low_balance_alert(user_id, address, balance)
                        self.user_manager.record_alert(user_id, address, current_time)
                        alerts_sent += 1
                        print(f"📤 Alert sent to user {user_id} for address {address[:10]}...")
                    else:
                        print(f"⏭️ Skipping alert for user {user_id} (recently sent)")
                else:
                    print(f"✅ Balance OK for user {user_id}: {address[:10]}...{address[-8:]} = {balance:.6f} BNB (threshold: {threshold})")

        print(f"✅ Balance check completed: {success_count} successful, {failed_count} failed, {alerts_sent} alerts sent")
    
    async def monitor_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                await self.check_all_balances()
            except Exception as e:
                print(f"❌ Error in monitor loop: {str(e)}")
            
            # 等待下次检查
            await asyncio.sleep(CHECK_INTERVAL * 60)  # 转换为秒
    
    def start_monitoring(self):
        """开始监控"""
        if self.is_running:
            print("⚠️ Monitor is already running")
            return
        
        self.is_running = True
        print(f"🚀 Starting balance monitor (check interval: {CHECK_INTERVAL} minutes)")
        
        # 在后台任务中运行监控循环
        asyncio.create_task(self.monitor_loop())
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        print("🛑 Balance monitor stopped")
    
    async def manual_check(self):
        """手动检查（用于测试）"""
        print("🔄 Manual balance check triggered")
        await self.check_all_balances()
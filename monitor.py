import asyncio
import time
from bsc_api import BSCBalanceChecker
from user_manager import UserManager
from telegram_bot import GasAlertBot
from config import LOW_BALANCE_THRESHOLD, CHECK_INTERVAL

class BalanceMonitor:
    def __init__(self, bot: GasAlertBot):
        self.balance_checker = BSCBalanceChecker()
        self.user_manager = UserManager()
        self.bot = bot
        self.is_running = False
    
    async def check_all_balances(self):
        """检查所有监控地址的余额"""
        print(f"⏰ Starting balance check at {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 重新加载用户数据以获取最新的地址列表
        self.user_manager.users_data = self.user_manager.load_data()

        address_to_users = self.user_manager.get_user_addresses_mapping()
        current_time = time.time()
        
        alerts_sent = 0
        addresses_checked = 0
        
        for address, user_ids in address_to_users.items():
            try:
                addresses_checked += 1
                is_low, balance = self.balance_checker.check_low_balance(address, LOW_BALANCE_THRESHOLD)
                
                if is_low:
                    print(f"🔴 Low balance detected: {address[:10]}...{address[-8:]} = {balance:.6f} BNB")
                    
                    for user_id in user_ids:
                        if self.user_manager.should_send_alert(user_id, address, current_time):
                            await self.bot.send_low_balance_alert(user_id, address, balance)
                            self.user_manager.record_alert(user_id, address, current_time)
                            alerts_sent += 1
                            print(f"📤 Alert sent to user {user_id} for address {address[:10]}...")
                        else:
                            print(f"⏭️ Skipping alert for user {user_id} (recently sent)")
                else:
                    print(f"✅ Balance OK: {address[:10]}...{address[-8:]} = {balance:.6f} BNB")
                    
                # 避免API调用过于频繁
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Error checking balance for {address[:10]}...{address[-8:]}: {str(e)}")
        
        print(f"✅ Balance check completed: {addresses_checked} addresses checked, {alerts_sent} alerts sent")
    
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
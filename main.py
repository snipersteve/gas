#!/usr/bin/env python3
"""
BSC Gas余额监控机器人
功能：监控BSC链上钱包BNB余额，当余额低于0.05 BNB时通过Telegram推送提醒
"""

import asyncio
import sys
import signal
from telegram_bot import GasAlertBot
from monitor import BalanceMonitor
from config import TELEGRAM_BOT_TOKEN, ETHERSCAN_API_KEY

def check_config():
    """检查配置是否完整"""
    if TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ 错误: 请在 .env 文件中设置 TELEGRAM_BOT_TOKEN")
        return False
    
    if ETHERSCAN_API_KEY == 'YourApiKeyToken':
        print("❌ 错误: 请在 .env 文件中设置 ETHERSCAN_API_KEY")
        return False
    
    return True

class GasAlertService:
    def __init__(self):
        self.bot = None
        self.monitor = None
        self.running = False
    
    async def start(self):
        """启动服务"""
        if not check_config():
            sys.exit(1)
        
        print("🚀 Gas Alert Bot Service Starting...")
        
        try:
            # 初始化机器人
            self.bot = GasAlertBot()
            
            # 初始化监控器
            self.monitor = BalanceMonitor(self.bot)
            
            # 启动监控
            self.monitor.start_monitoring()
            
            # 设置信号处理
            self.setup_signal_handlers()
            
            self.running = True
            print("✅ Service started successfully!")
            print("📱 Bot is ready to receive messages")
            print("⏰ Balance monitoring is active")
            print("Press Ctrl+C to stop")
            
            # 运行机器人（阻塞）
            await self.bot.application.initialize()
            await self.bot.application.start()
            await self.bot.application.updater.start_polling()
            
            # 保持运行直到收到停止信号
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Received stop signal")
        except Exception as e:
            print(f"❌ Service error: {str(e)}")
        finally:
            await self.stop()
    
    async def stop(self):
        """停止服务"""
        print("🔄 Stopping service...")
        
        self.running = False
        
        if self.monitor:
            self.monitor.stop_monitoring()
        
        if self.bot:
            try:
                await self.bot.application.updater.stop()
                await self.bot.application.stop()
                await self.bot.application.shutdown()
            except Exception as e:
                print(f"Warning: Error stopping bot: {e}")
        
        print("✅ Service stopped")
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            print(f"\n📡 Received signal {signum}")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """主函数"""
    service = GasAlertService()
    try:
        await service.start()
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # 创建 .env 示例文件
    try:
        with open('.env.example', 'w') as f:
            f.write("""# Telegram Bot Token (从 @BotFather 获取)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Etherscan API Key (从 https://etherscan.io/apis 获取)
ETHERSCAN_API_KEY=your_etherscan_api_key_here
""")
        print("📝 Created .env.example file")
    except:
        pass
    
    # 运行主程序
    asyncio.run(main())
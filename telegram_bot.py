import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from bsc_api import BSCBalanceChecker
from user_manager import UserManager
from config import TELEGRAM_BOT_TOKEN, LOW_BALANCE_THRESHOLD

class GasAlertBot:
    def __init__(self):
        self.balance_checker = BSCBalanceChecker()
        self.user_manager = UserManager()
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """设置消息处理器"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("add", self.add_address_command))
        self.application.add_handler(CommandHandler("list", self.list_addresses_command))
        self.application.add_handler(CommandHandler("remove", self.remove_address_command))
        self.application.add_handler(CommandHandler("check", self.check_balance_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_address))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """开始命令"""
        user_id = update.effective_user.id
        welcome_message = (
            "🚀 欢迎使用BSC Gas余额监控机器人！\n\n"
            "📝 使用方法：\n"
            "• 直接发送钱包地址进行监控\n"
            "• /add <地址> - 添加监控地址\n"
            "• /list - 查看监控列表\n"
            "• /remove <地址> - 移除监控\n"
            "• /check - 立即检查所有地址\n"
            "• /help - 查看帮助\n\n"
            f"⚠️ 当BNB余额低于 {LOW_BALANCE_THRESHOLD} 时会自动推送提醒"
        )
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """帮助命令"""
        help_message = (
            "📋 命令列表：\n\n"
            "/start - 开始使用机器人\n"
            "/add <地址> - 添加监控地址\n"
            "/list - 查看当前监控的地址\n"
            "/remove <地址> - 移除监控地址\n"
            "/check - 立即检查所有地址余额\n"
            "/help - 显示此帮助信息\n\n"
            "💡 提示：\n"
            "• 直接发送钱包地址也可以添加监控\n"
            "• 地址格式：0x开头的42位十六进制字符\n"
            f"• 余额低于 {LOW_BALANCE_THRESHOLD} BNB 时会收到提醒"
        )
        await update.message.reply_text(help_message)
    
    async def add_address_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """添加地址命令"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text("❌ 请提供要监控的钱包地址\n例如：/add 0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511")
            return
        
        address = context.args[0].strip()
        await self.add_address(update, user_id, address)
    
    async def handle_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理直接发送的地址"""
        user_id = update.effective_user.id
        address = update.message.text.strip()
        
        if self.balance_checker.is_valid_address(address):
            await self.add_address(update, user_id, address)
        else:
            await update.message.reply_text(
                "❌ 无效的钱包地址格式\n\n"
                "请发送有效的BSC钱包地址（以0x开头的42位字符）\n"
                "或使用 /help 查看使用说明"
            )
    
    async def add_address(self, update: Update, user_id: int, address: str):
        """添加地址到监控列表"""
        if not self.balance_checker.is_valid_address(address):
            await update.message.reply_text("❌ 无效的钱包地址格式")
            return
        
        try:
            # 检查当前余额
            balance = self.balance_checker.get_bnb_balance(address)
            
            # 添加到用户监控列表
            if self.user_manager.add_address(user_id, address):
                status = "🔴 余额不足" if balance < LOW_BALANCE_THRESHOLD else "✅ 余额充足"
                await update.message.reply_text(
                    f"✅ 地址添加成功！\n\n"
                    f"📍 地址: {address[:10]}...{address[-8:]}\n"
                    f"💰 当前余额: {balance:.6f} BNB\n"
                    f"📊 状态: {status}"
                )
            else:
                await update.message.reply_text("ℹ️ 该地址已在监控列表中")
                
        except Exception as e:
            await update.message.reply_text(f"❌ 添加失败: {str(e)}")
    
    async def list_addresses_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """列出监控地址"""
        user_id = update.effective_user.id
        addresses = self.user_manager.get_addresses(user_id)
        
        if not addresses:
            await update.message.reply_text("📝 您还没有添加任何监控地址\n\n发送钱包地址开始监控！")
            return
        
        message = "📋 您的监控列表：\n\n"
        for i, address in enumerate(addresses, 1):
            try:
                balance = self.balance_checker.get_bnb_balance(address)
                status = "🔴" if balance < LOW_BALANCE_THRESHOLD else "✅"
                message += f"{i}. {status} {address[:10]}...{address[-8:]}\n   💰 {balance:.6f} BNB\n\n"
            except Exception as e:
                message += f"{i}. ❌ {address[:10]}...{address[-8:]}\n   ⚠️ 查询失败: {str(e)[:30]}...\n\n"
        
        await update.message.reply_text(message)
    
    async def remove_address_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """移除监控地址"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text("❌ 请提供要移除的钱包地址\n例如：/remove 0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511")
            return
        
        address = context.args[0].strip()
        
        if self.user_manager.remove_address(user_id, address):
            await update.message.reply_text(f"✅ 地址 {address[:10]}...{address[-8:]} 已移除监控")
        else:
            await update.message.reply_text("❌ 地址不在监控列表中")
    
    async def check_balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """立即检查余额"""
        user_id = update.effective_user.id
        addresses = self.user_manager.get_addresses(user_id)
        
        if not addresses:
            await update.message.reply_text("📝 您还没有添加任何监控地址")
            return
        
        await update.message.reply_text("🔄 正在检查所有地址余额...")
        
        low_balance_count = 0
        total_count = len(addresses)
        
        for address in addresses:
            try:
                is_low, balance = self.balance_checker.check_low_balance(address, LOW_BALANCE_THRESHOLD)
                if is_low:
                    low_balance_count += 1
                    await update.message.reply_text(
                        f"🔴 余额不足警告！\n\n"
                        f"📍 地址: {address[:10]}...{address[-8:]}\n"
                        f"💰 余额: {balance:.6f} BNB\n"
                        f"⚠️ 低于阈值: {LOW_BALANCE_THRESHOLD} BNB"
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ 检查失败\n📍 地址: {address[:10]}...{address[-8:]}\n⚠️ 错误: {str(e)}"
                )
        
        summary = f"✅ 检查完成！\n📊 总计: {total_count} 个地址\n🔴 余额不足: {low_balance_count} 个"
        await update.message.reply_text(summary)
    
    async def send_low_balance_alert(self, user_id: int, address: str, balance: float):
        """发送余额不足警告"""
        try:
            message = (
                f"🚨 GAS余额不足警告！\n\n"
                f"📍 地址: {address[:10]}...{address[-8:]}\n"
                f"💰 当前余额: {balance:.6f} BNB\n"
                f"⚠️ 阈值: {LOW_BALANCE_THRESHOLD} BNB\n\n"
                f"请及时充值以确保交易正常进行！"
            )
            await self.application.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Failed to send alert to user {user_id}: {str(e)}")
    
    def run(self):
        """运行机器人"""
        print("🤖 Gas Alert Bot is starting...")
        self.application.run_polling()
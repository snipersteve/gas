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
        self.application.add_handler(CommandHandler("setthreshold", self.set_threshold_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_address))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """开始命令"""
        user_id = update.effective_user.id
        threshold = self.user_manager.get_threshold(user_id)
        welcome_message = (
            "🚀 欢迎使用BSC Gas余额监控机器人！\n\n"
            "📝 使用方法：\n"
            "• 直接发送钱包地址进行监控\n"
            "• /add <地址> - 添加监控地址\n"
            "• /list - 查看监控列表\n"
            "• /remove <地址> - 移除监控\n"
            "• /check - 立即检查所有地址\n"
            "• /setthreshold <数值> - 设置余额阈值\n"
            "• /help - 查看帮助\n\n"
            f"⚠️ 当前余额阈值: {threshold} BNB\n"
            f"余额低于该值时会自动推送提醒"
        )
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """帮助命令"""
        user_id = update.effective_user.id
        threshold = self.user_manager.get_threshold(user_id)
        help_message = (
            "📋 命令列表：\n\n"
            "/start - 开始使用机器人\n"
            "/add <地址> - 添加监控地址\n"
            "/list - 查看当前监控的地址\n"
            "/remove <地址> - 移除监控地址\n"
            "/check - 立即检查所有地址余额\n"
            "/setthreshold <数值> - 设置余额阈值\n"
            "/help - 显示此帮助信息\n\n"
            "💡 提示：\n"
            "• 直接发送钱包地址也可以添加监控\n"
            "• 地址格式：0x开头的42位十六进制字符\n"
            f"• 当前余额阈值: {threshold} BNB\n"
            "• 设置阈值示例: /setthreshold 0.1"
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
        """添加地址到监控列表（带重试机制）"""
        if not self.balance_checker.is_valid_address(address):
            await update.message.reply_text("❌ 无效的钱包地址格式")
            return

        # 带重试的余额查询
        max_retries = 3
        balance = None

        for attempt in range(max_retries):
            try:
                balance = await self.balance_checker.get_bnb_balance(address)
                break  # 成功则跳出
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    await asyncio.sleep(wait_time)
                else:
                    await update.message.reply_text(f"❌ 查询余额失败（已重试{max_retries}次）: {str(e)}")
                    return

        # 添加到用户监控列表
        if self.user_manager.add_address(user_id, address):
            threshold = self.user_manager.get_threshold(user_id)
            status = "🔴 余额不足" if balance < threshold else "✅ 余额充足"
            await update.message.reply_text(
                f"✅ 地址添加成功！\n\n"
                f"📍 地址: {address[:10]}...{address[-8:]}\n"
                f"💰 当前余额: {balance:.6f} BNB\n"
                f"⚠️ 阈值设置: {threshold} BNB\n"
                f"📊 状态: {status}"
            )
        else:
            await update.message.reply_text("ℹ️ 该地址已在监控列表中")
    
    async def query_address_with_retry(self, address: str):
        """查询单个地址余额（单次尝试）"""
        try:
            balance = await self.balance_checker.get_bnb_balance(address)
            return {'address': address, 'balance': balance, 'success': True}
        except Exception as e:
            return {'address': address, 'balance': 0.0, 'success': False, 'error': str(e)}

    async def query_batch_with_delay(self, addresses, delay_between_requests=0.3):
        """批量查询地址，请求之间有延迟以避免触发API限制"""
        results = []
        for address in addresses:
            result = await self.query_address_with_retry(address)
            results.append(result)
            # 每个请求后都添加延迟，包括最后一个（0.3秒 = 每秒3.3次）
            await asyncio.sleep(delay_between_requests)
        return results

    async def list_addresses_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """列出监控地址（带批次重试机制）"""
        user_id = update.effective_user.id
        addresses = self.user_manager.get_addresses(user_id)

        if not addresses:
            await update.message.reply_text("📝 您还没有添加任何监控地址\n\n发送钱包地址开始监控！")
            return

        await update.message.reply_text("🔄 正在查询地址余额...")

        # 批次重试逻辑
        successful_results = {}
        addresses_to_query = addresses.copy()
        retry_round = 0
        max_retry_rounds = 5  # list命令最多重试5轮

        while addresses_to_query and retry_round < max_retry_rounds:
            retry_round += 1

            if retry_round > 1:
                wait_time = min(retry_round * 2, 10)
                await asyncio.sleep(wait_time)

            # 限速查询：请求之间有0.3秒延迟（每秒3.3次）
            results = await self.query_batch_with_delay(addresses_to_query, delay_between_requests=0.3)

            # 分离成功和失败
            failed_addresses = []
            for result in results:
                if result['success']:
                    successful_results[result['address']] = result['balance']
                else:
                    failed_addresses.append(result['address'])

            addresses_to_query = failed_addresses

        # 生成消息
        threshold = self.user_manager.get_threshold(user_id)
        message = f"📋 您的监控列表：\n\n⚠️ 当前阈值: {threshold} BNB\n\n"
        for i, address in enumerate(addresses, 1):
            if address in successful_results:
                balance = successful_results[address]
                status = "🔴" if balance < threshold else "✅"
                message += f"{i}. {status} {address[:10]}...{address[-8:]}\n   💰 {balance:.6f} BNB\n\n"
            else:
                message += f"{i}. ❌ {address[:10]}...{address[-8:]}\n   ⚠️ 查询失败（已重试{retry_round}次）\n\n"

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
        """立即检查余额（带批次重试机制）"""
        user_id = update.effective_user.id
        addresses = self.user_manager.get_addresses(user_id)

        if not addresses:
            await update.message.reply_text("📝 您还没有添加任何监控地址")
            return

        await update.message.reply_text("🔄 正在检查所有地址余额...")

        # 批次重试逻辑
        successful_results = {}
        addresses_to_query = addresses.copy()
        retry_round = 0
        max_retry_rounds = 5

        while addresses_to_query and retry_round < max_retry_rounds:
            retry_round += 1

            if retry_round > 1:
                wait_time = min(retry_round * 2, 10)
                await asyncio.sleep(wait_time)

            # 限速查询：请求之间有0.3秒延迟（每秒3.3次）
            results = await self.query_batch_with_delay(addresses_to_query, delay_between_requests=0.3)

            # 分离成功和失败
            failed_addresses = []
            for result in results:
                if result['success']:
                    successful_results[result['address']] = result['balance']
                else:
                    failed_addresses.append(result['address'])

            addresses_to_query = failed_addresses

        # 统计并发送警告
        threshold = self.user_manager.get_threshold(user_id)
        low_balance_count = 0
        failed_count = len(addresses) - len(successful_results)

        for address in addresses:
            if address in successful_results:
                balance = successful_results[address]
                if balance < threshold:
                    low_balance_count += 1
                    await update.message.reply_text(
                        f"🔴 余额不足警告！\n\n"
                        f"📍 地址: {address[:10]}...{address[-8:]}\n"
                        f"💰 余额: {balance:.6f} BNB\n"
                        f"⚠️ 低于阈值: {threshold} BNB"
                    )
            else:
                await update.message.reply_text(
                    f"❌ 检查失败\n📍 地址: {address[:10]}...{address[-8:]}\n⚠️ 已重试{retry_round}次仍失败"
                )

        summary = f"✅ 检查完成！\n📊 总计: {len(addresses)} 个地址\n✅ 成功: {len(successful_results)} 个\n❌ 失败: {failed_count} 个\n🔴 余额不足: {low_balance_count} 个"
        await update.message.reply_text(summary)
    
    async def send_low_balance_alert(self, user_id: int, address: str, balance: float):
        """发送余额不足警告"""
        try:
            threshold = self.user_manager.get_threshold(user_id)
            message = (
                f"🚨 GAS余额不足警告！\n\n"
                f"📍 地址: {address[:10]}...{address[-8:]}\n"
                f"💰 当前余额: {balance:.6f} BNB\n"
                f"⚠️ 阈值: {threshold} BNB\n\n"
                f"请及时充值以确保交易正常进行！"
            )
            await self.application.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Failed to send alert to user {user_id}: {str(e)}")

    async def set_threshold_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """设置余额阈值命令"""
        user_id = update.effective_user.id

        if not context.args:
            current_threshold = self.user_manager.get_threshold(user_id)
            await update.message.reply_text(
                f"⚠️ 请提供阈值数值\n\n"
                f"当前阈值: {current_threshold} BNB\n\n"
                f"使用方法：/setthreshold 0.1\n"
                f"示例：设置为0.1个BNB"
            )
            return

        try:
            threshold = float(context.args[0])

            if threshold <= 0:
                await update.message.reply_text("❌ 阈值必须大于0")
                return

            if threshold > 100:
                await update.message.reply_text("❌ 阈值不能超过100 BNB")
                return

            self.user_manager.set_threshold(user_id, threshold)
            await update.message.reply_text(
                f"✅ 余额阈值已更新！\n\n"
                f"⚠️ 新阈值: {threshold} BNB\n"
                f"当余额低于此值时会收到提醒"
            )
        except ValueError:
            await update.message.reply_text(
                "❌ 无效的数值格式\n\n"
                "请输入有效的数字，例如：\n"
                "/setthreshold 0.05\n"
                "/setthreshold 0.1"
            )
    
    def run(self):
        """运行机器人"""
        print("🤖 Gas Alert Bot is starting...")
        self.application.run_polling()
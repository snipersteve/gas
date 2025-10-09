# BSC Gas余额监控机器人

一个基于Python的Telegram机器人，用于监控BSC链上钱包的BNB余额，当余额低于设定阈值时自动推送提醒。

## 功能特性

- 🔍 监控BSC链上钱包BNB余额
- ⚠️ 余额低于0.05 BNB时自动推送提醒
- 🤖 Telegram机器人交互界面
- 📱 支持多用户多地址监控
- ⏰ 定时自动检查（每30分钟）
- 🚫 防重复推送（24小时内同一地址不重复提醒）

## 部署方式

### 方式一：Docker部署（推荐）

#### 1. 克隆项目

```bash
git clone <repository_url>
cd gas
```

#### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# Telegram Bot Token (从 @BotFather 获取)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Etherscan API Key (从 https://etherscan.io/apis 获取)
ETHERSCAN_API_KEY=your_etherscan_api_key_here
```

#### 3. 使用Docker Compose启动

```bash
# 构建并启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

#### 4. 手动Docker部署

```bash
# 构建镜像
docker build -t gas-alert-bot .

# 运行容器
docker run -d \
  --name gas-alert-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/user_data.json:/app/user_data.json \
  --env-file .env \
  gas-alert-bot

# 查看日志
docker logs -f gas-alert-bot
```

### 方式二：传统部署

#### 1. 克隆项目

```bash
git clone <repository_url>
cd gas
```

#### 2. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# Telegram Bot Token (从 @BotFather 获取)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Etherscan API Key (从 https://etherscan.io/apis 获取)
ETHERSCAN_API_KEY=your_etherscan_api_key_here
```

### 4. 获取必要的API密钥

#### Telegram Bot Token
1. 在Telegram中找到 @BotFather
2. 发送 `/newbot` 创建新机器人
3. 按提示设置机器人名称和用户名
4. 复制返回的token

#### Etherscan API Key
1. 访问 https://etherscan.io/apis
2. 注册账户并登录
3. 创建新的API Key
4. 复制API Key

## 使用方法

#### 4. 启动程序

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行程序
python main.py
```

### Telegram机器人命令

- `/start` - 开始使用机器人
- `/help` - 查看帮助信息
- `/add <地址>` - 添加监控地址
- `/list` - 查看当前监控的地址
- `/remove <地址>` - 移除监控地址
- `/check` - 立即检查所有地址余额

### 直接发送地址

也可以直接向机器人发送钱包地址（以0x开头的42位字符），系统会自动添加到监控列表。

## 配置说明

在 `config.py` 中可以调整以下参数：

- `LOW_BALANCE_THRESHOLD` - 余额阈值（默认0.05 BNB）
- `CHECK_INTERVAL` - 检查间隔（默认30分钟）
- `BSC_CHAIN_ID` - BSC链ID（默认56）

## 文件结构

```
gas/
├── main.py              # 主程序入口
├── config.py            # 配置文件
├── bsc_api.py          # BSC余额查询API
├── telegram_bot.py     # Telegram机器人
├── user_manager.py     # 用户数据管理
├── monitor.py          # 余额监控逻辑
├── requirements.txt    # Python依赖
├── .env.example       # 环境变量示例
├── Dockerfile         # Docker镜像构建文件
├── docker-compose.yml # Docker Compose配置
├── .dockerignore      # Docker忽略文件
└── README.md          # 说明文档
```

## 运行原理

1. 用户通过Telegram机器人添加要监控的BSC钱包地址
2. 程序定时调用Etherscan API查询地址的BNB余额
3. 当余额低于设定阈值时，自动向用户发送Telegram消息提醒
4. 支持多用户使用，每个用户可以监控多个地址
5. 防止重复推送，24小时内同一地址不会重复提醒

## 注意事项

- 确保Etherscan API Key有足够的调用次数限制
- 程序需要持续运行以保持监控功能
- **Docker部署**：推荐使用Docker部署，自动重启和日志管理
- **传统部署**：建议在服务器上使用 `screen` 或 `tmux` 等工具后台运行
- 用户数据存储在 `user_data.json` 文件中，Docker部署时会自动挂载到主机

## Docker相关命令

```bash
# 查看容器状态
docker-compose ps

# 查看实时日志
docker-compose logs -f gas-alert-bot

# 进入容器
docker-compose exec gas-alert-bot bash

# 更新并重启
docker-compose pull && docker-compose up -d

# 备份用户数据
docker-compose exec gas-alert-bot cp user_data.json /app/data/backup.json
```

## 故障排除

### 常见问题

1. **API调用失败**
   - 检查Etherscan API Key是否正确
   - 检查网络连接是否正常
   - 确认API调用次数未超限

2. **机器人无响应**
   - 检查Telegram Bot Token是否正确
   - 确认机器人是否被正确启动
   - 查看控制台错误日志

3. **地址验证失败**
   - 确认地址格式正确（0x开头的42位字符）
   - 检查是否为有效的以太坊/BSC地址

## 许可证

MIT License
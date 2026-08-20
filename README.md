# Bot-hosting 自动续期（多账号版）

> 基于 SeleniumBase 和 GitHub Actions，自动续期 [Bot‑hosting.net](https://bot‑hosting.net) 的免费服务，支持多账号、自动处理 Turnstile 人机验证，并通过 Telegram 推送结果通知。

---

## 📖 项目简介

本项目通过模拟浏览器操作，自动登录 Bot‑hosting 账单页面，检测并点击续期按钮，完成后可自动更新 `SESSION_TOKEN` 并发送通知。  
**核心亮点**：

- ✅ **双登录机制**：优先使用 `SESSION_TOKEN`，失效后自动切换 Discord OAuth（需提供 `DISCORD_TOKEN`）。
- ✅ **自动处理 Turnstile**：利用 SeleniumBase 的 `uc` 模式点击验证，保留核心逻辑以保证高通过率。
- ✅ **多账号支持**：通过 `ACCOUNTS_JSON` 环境变量批量管理多个账号，依次续期。
- ✅ **代理支持**：可配置 HTTP 代理，适用于受限网络环境（如国内服务器）。
- ✅ **GitHub Secrets 自动更新**（单账号模式）：自动将新 `SESSION_TOKEN` 写回仓库 Secret。
- ✅ **Telegram 通知**：续期成功/失败/未到期等状态实时推送。

---

## 🚀 功能特性

- 每日定时执行（可自定义 cron）
- 支持 `workflow_dispatch` 手动触发
- 无头浏览器运行，节省资源
- 随机延迟降低风控
- 完整的日志输出，便于调试

---

## 📦 前置要求

- **GitHub 仓库**（推荐使用 Actions 自动运行）
- **Secrets 配置**（见下文）
- （本地运行）Python 3.12+，安装依赖：`seleniumbase`, `requests`，并安装 Chrome 浏览器

---

## 🔧 配置说明

### 1. GitHub Secrets 设置

在仓库 `Settings` → `Secrets and variables` → `Actions` 中添加以下 Secrets：

| Secret 名称 | 说明 | 是否必须 |
|------------|------|---------|
| `SESSION_TOKEN` | Bot‑hosting 的会话令牌（从浏览器 Cookie 中获取） | 可选（至少提供一种登录方式） |
| `DISCORD_TOKEN` | Discord 用户令牌（用于 OAuth 登录） | 可选（至少提供一种登录方式） |
| `EMAIL` | 账号邮箱（仅用于通知显示） | 推荐 |
| `GH_TOKEN` | GitHub Personal Access Token（用于自动更新 SESSION_TOKEN） | 可选（单账号模式推荐） |
| `TG_BOT_TOKEN` | Telegram Bot Token | 可选（如需通知） |
| `TG_CHAT_ID` | Telegram 接收消息的 Chat ID | 可选（如需通知） |
| `ACCOUNTS_JSON` | 多账号 JSON 配置（详见下文） | 可选（多账号模式必须） |
| `NODE_LINK` | （可选）代理订阅链接，用于 `sing‑box` 代理 | 可选 |
| `HEADLESS` | 是否无头模式（`true`/`false`） | 可选，默认 `false` |
| `IS_PROXY` | 是否启用代理（`true`/`false`） | 可选，默认 `false` |
| `PROXY_SERVER` | 代理地址（如 `http://127.0.0.1:1080`） | 可选，默认 `http://127.0.0.1:1080` |

---

### 2. 单账号模式（传统方式）

在 Secrets 中配置 `SESSION_TOKEN` 或 `DISCORD_TOKEN`（至少一个），以及 `EMAIL`、`GH_TOKEN`（如需自动更新）等。脚本会直接使用这些变量。

---

### 3. 多账号模式（推荐）

在 Secrets 中添加 `ACCOUNTS_JSON`，其值为一个 JSON 数组，每个元素包含以下字段：

```json
[
  {
    "email": "account1@gmail.com",
    "session_token": "MTA...",
    "discord_token": "MTE...",
    "label": "主账号"          // 可选，用于通知显示
  },
  {
    "email": "account2@outlook.com",
    "discord_token": "NTI...",
    "label": "小号"
  }
]
```

- `email` 和 `label` 仅用于通知，不参与验证。
- 每个账号至少提供 `session_token` 或 `discord_token`（建议两者都提供，提高容错）。
- 多账号模式下，`GH_TOKEN` 会被脚本自动忽略（避免互相覆盖），您需定期手动更新 JSON 中的 Token（或自行扩展逻辑）。

---

## 🛠 使用方法

### 方式一：GitHub Actions（推荐）

1. Fork 本仓库。
2. 按上述说明配置 Secrets。
3. 默认每天 UTC 1:00（北京时间 9:00）自动运行，也可在 Actions 页面手动触发 `workflow_dispatch`。
4. 查看运行日志和 Telegram 通知结果。

### 方式二：本地运行

```bash
# 安装依赖
pip install seleniumbase requests

# 安装 Chrome 浏览器（Linux）
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update && sudo apt-get install -y google-chrome-stable

# 设置环境变量（示例）
export SESSION_TOKEN="your_session_token"
export DISCORD_TOKEN="your_discord_token"
export EMAIL="your_email"
export TG_BOT_TOKEN="your_bot_token"
export TG_CHAT_ID="your_chat_id"
export HEADLESS="true"
# 若有代理
export IS_PROXY="true"
export PROXY_SERVER="http://127.0.0.1:1080"

# 运行脚本
xvfb-run --auto-servernum python3 app.py
```

---

## 📋 工作流说明

GitHub Actions 工作流（`.github/workflows/renew.yml`）会执行以下步骤：

1. 检出代码、设置 Python 3.12。
2. 安装系统依赖（XVFB、Chrome、中文字体等）和 Python 依赖。
3. （可选）下载并启动 sing‑box 代理（需 `NODE_LINK`）。
4. 运行 `app.py`，完成所有账号的续期。
5. 清理进程和临时文件。
6. 自动保留最近 1 次运行记录，删除更旧的记录。

> 工作流文件位于仓库的 `.github/workflows/` 目录下，可自行调整 cron 时间。

---

## ⚠️ 注意事项

- **人机验证**：Turnstile 验证采用 `uc_gui_click_captcha()` 方式，该方式可能因网站更新而失效。若频繁失败，请更新 SeleniumBase 或调整等待逻辑。
- **代理安全**：若使用外部代理脚本，请确保其来源可信，避免安全风险。
- **多账号风控**：连续处理多个账号可能触发 IP 风控，建议开启代理并增加延迟（脚本已内置随机延迟 5～15 秒）。
- **SESSION_TOKEN 获取**：登录 Bot‑hosting 后，在浏览器开发者工具中复制 Cookie 中的 `session_token` 值。
- **Discord Token 权限**：需具备 `identify` 和 `email` 权限，建议使用用户 Token（非 Bot Token）。

---

## ❓ 常见问题

### Q: 如何获取 `SESSION_TOKEN`？
A: 在浏览器中登录 Bot‑hosting，按 F12 打开开发者工具 → Application → Cookies → `https://bot-hosting.net`，复制 `session_token` 的值。

### Q: 多账号模式下如何更新 Token？
A: 当前版本暂不支持自动更新多账号的 JSON Secret，您需要手动更新 `ACCOUNTS_JSON` 中的 Token。您可以编写额外脚本调用 GitHub API 更新 Secret，或定期手动替换。

### Q: 运行日志显示 Turnstile 验证超时怎么办？
A: 可尝试增加等待时间（修改 `wait_for_turnstile_pass` 的 `timeout` 参数），或检查代理是否稳定。

### Q: 如何禁用无头模式以便调试？
A: 在 Secrets 中设置 `HEADLESS=false`，然后在本地运行（不使用 `xvfb-run`）即可看到浏览器窗口。

---

## 📄 许可证

本项目基于 MIT 许可证开源，仅供学习交流使用。请遵守 Bot‑hosting 的服务条款，合理使用。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进脚本。如有疑问，请附上详细日志以便排查。

---

**Happy Auto Renew! 🎉**

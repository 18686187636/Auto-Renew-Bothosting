# 🚀 Bot‑hosting 多账号自动续期

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-自动续期-blue?logo=githubactions)](.github/workflows/renew.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green?logo=python)](https://www.python.org/)

> 通过 GitHub Actions 定时为 [bot‑hosting.net](https://bot‑hosting.net) 的多个账号自动续期免费计划（每 4 天续期一次），并自动更新过期的 `SESSION_TOKEN`，全程无人值守。

---

## 📖 目录

- [功能特点](#-功能特点)
- [准备工作](#-准备工作)
- [配置说明](#-配置说明)
  - [环境变量](#-环境变量)
  - [GitHub Secrets](#-github-secrets)
  - [账号 JSON 格式](#-账号-json-格式)
- [GitHub Actions 工作流](#-github-actions-工作流)
- [本地运行](#-本地运行)
- [获取凭据教程](#-获取凭据教程)
- [常见问题](#-常见问题)
- [许可证](#-许可证)

---

## ✨ 功能特点

- ✅ **多账号支持** – 使用单个 JSON 数组管理任意数量的账号。
- ✅ **双登录机制** – 优先使用 `SESSION_TOKEN`，失效后自动切换至 Discord OAuth（基于 `DISCORD_TOKEN`）。
- ✅ **自动续期** – 检测并点击“Renew”按钮，通过 Turnstile 验证，续期 4 天。
- ✅ **智能 Token 更新** – 续期成功后自动提取新的 `SESSION_TOKEN` 并更新到 GitHub Secrets（需 `GH_TOKEN` 权限）。
- ✅ **通知推送** – 支持 Telegram 实时通知每个账号的执行结果。
- ✅ **代理支持** – 可配置 HTTP 代理，适应网络环境。
- ✅ **完全无头运行** – 适配 GitHub Actions 无图形化环境。

---

## 🛠 准备工作

1. **Fork 或 Clone 本仓库**，并将以下两个文件放入仓库：
   - 脚本文件（如 `renew.py`）
   - GitHub Actions 工作流（`.github/workflows/renew.yml`）

2. **准备各账号的登录凭据**（至少提供 `session_token` 或 `discord_token` 之一）：
   - 从浏览器 Cookie 获取 `session_token`。
   - 或从 Discord 开发者工具获取 `discord_token`。

3. **（可选）** 准备一个具有 **写权限** 的 GitHub Personal Access Token（`GH_TOKEN`），用于自动更新 Secrets。

4. **（可选）** 准备 Telegram Bot Token 和 Chat ID，用于接收通知。

---

## ⚙️ 配置说明

### 🔐 GitHub Secrets

在仓库 **Settings → Secrets and variables → Actions** 中设置以下 Secrets：

| Secret 名称 | 是否必须 | 说明 |
|-------------|----------|------|
| `ACCOUNTS_JSON` | ✅ **必须** | 多账号 JSON 数组（格式见下文）。 |
| `GH_TOKEN` | ⭐ 推荐 | GitHub PAT，需要 `repo` 或 `workflow` 权限，用于自动更新 `SESSION_TOKEN`。 |
| `TG_BOT_TOKEN` | 可选 | Telegram Bot Token，用于通知。 |
| `TG_CHAT_ID` | 可选 | 接收通知的 Telegram 用户/群组 ID。 |

> **注意**：若使用单账号且不设置 `ACCOUNTS_JSON`，脚本会回退到传统的 `EMAIL`、`SESSION_TOKEN` 等环境变量（兼容旧版），但推荐统一使用 `ACCOUNTS_JSON`。

---

### 📦 账号 JSON 格式

`ACCOUNTS_JSON` 是一个 JSON 数组，每个元素代表一个账号：

```json
[
  {
    "email": "user1@example.com",
    "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "secret_name": "SESSION_TOKEN"
  },
  {
    "email": "user2@gmail.com",
    "discord_token": "MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.G...",
    "secret_name": "SESSION_TOKEN_2"
  },
  {
    "email": "user3@outlook.com",
    "session_token": "abc...",
    "discord_token": "def...",
    "secret_name": "MY_CUSTOM_TOKEN"
  }
]
```

**字段说明：**

| 字段 | 必填 | 描述 |
|------|------|------|
| `email` | ✅ | 仅用于通知和日志显示，可任意填写。 |
| `session_token` | ⚠️ 至少其一 | bot‑hosting 的登录 Cookie（优先使用）。 |
| `discord_token` | ⚠️ 至少其一 | Discord 用户 Token，作为备用登录方式。 |
| `secret_name` | 可选 | 该账号的 `SESSION_TOKEN` 更新到哪个 GitHub Secret。若不指定，索引 0 使用 `SESSION_TOKEN`，索引 ≥1 使用 `SESSION_TOKEN_索引`。 |

---

### 🧰 环境变量（工作流或本地）

除了 Secrets，脚本还读取以下环境变量（可在工作流 `env` 中或本地 `.env` 中设置）：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `IS_PROXY` | `false` | 是否启用代理。 |
| `PROXY_SERVER` | `http://127.0.0.1:1080` | 代理服务器地址（仅在 `IS_PROXY=true` 时生效）。 |
| `HEADLESS` | `true` | 浏览器是否无头模式（建议 `true`）。 |
| `GH_TOKEN` | - | GitHub PAT（也可通过 Secret 传递）。 |
| `TG_BOT_TOKEN` | - | Telegram Bot Token。 |
| `TG_CHAT_ID` | - | Telegram 接收者 ID。 |

---

## ⚡ GitHub Actions 工作流

将以下内容保存为 `.github/workflows/renew.yml`：

```yaml
name: Bot-hosting Auto Renew

on:
  schedule:
    - cron: '0 0 * * *'          # 每天 UTC 00:00 运行（北京时间 08:00）
  workflow_dispatch:             # 支持手动触发

jobs:
  renew:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: 安装依赖
        run: pip install seleniumbase requests
      - name: 执行续期
        env:
          ACCOUNTS: ${{ secrets.ACCOUNTS_JSON }}
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          TG_BOT_TOKEN: ${{ secrets.TG_BOT_TOKEN }}
          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
          HEADLESS: true
          # 如需代理，取消注释并设置
          # IS_PROXY: true
          # PROXY_SERVER: http://your-proxy:port
        run: python renew.py
```

---

## 🖥 本地运行

克隆仓库后，在本地终端执行：

```bash
# 安装依赖
pip install seleniumbase requests

# 设置环境变量（示例）
export ACCOUNTS='[{"email":"test@example.com","session_token":"xxx"}]'
export HEADLESS=false   # 本地调试时可关闭无头模式，查看浏览器操作

# 运行脚本
python renew.py
```

> 本地运行时需要安装 Chrome 浏览器及对应的 WebDriver（seleniumbase 会自动处理）。

---

## 🔑 获取凭据教程

### 获取 `session_token`
1. 在浏览器中登录 [bot‑hosting.net](https://bot‑hosting.net)。
2. 按 `F12` 打开开发者工具 → 切换到 **Application**（或 **存储**）标签。
3. 左侧找到 **Cookies** → `https://bot‑hosting.net`。
4. 找到名为 `session_token` 的 Cookie，复制其值（通常很长）。

### 获取 `discord_token`
1. 打开 Discord 网页版或桌面客户端，按 `F12` 进入开发者工具。
2. 切换到 **Network**（网络）标签，发送一条消息或刷新页面。
3. 在请求列表中找到任意一个请求（如 `science` 或 `messages`），查看 **Request Headers**。
4. 找到 `authorization` 字段，其值即为 Token（以 `MT...` 开头，长度约 70 字符）。

> ⚠️ **安全警告**：请勿将 Token 泄露给他人，否则可能导致账号被盗。

---

## ❓ 常见问题

**Q：为什么每天运行但经常显示“未到续期时间”？**  
A：续期按钮只在到期前 4 天出现，平时执行会提示倒计时，属于正常行为，无需担心。

**Q：Turnstile 验证失败怎么办？**  
A：脚本会自动重试 3 次，若仍失败会通过 Telegram 告警。建议保持 `HEADLESS=false` 本地测试一次，确保验证码可正常处理。网络环境（代理/IP）也可能影响，可尝试更换代理。

**Q：如何查看详细运行日志？**  
A：在 GitHub Actions 的 Workflow 页面点击对应任务，即可看到完整控制台输出。

**Q：`GH_TOKEN` 需要什么权限？**  
A：至少需要 `repo` 或 `workflow` 写入权限。推荐创建一个专用的 Fine‑grained PAT，仅授予目标仓库的 Secrets 读写权限。

**Q：我可以用 `ACCOUNTS_JSON` 和旧的环境变量混用吗？**  
A：脚本优先使用 `ACCOUNTS_JSON`，如果该变量不存在或解析失败，才会回退到单账号变量（`EMAIL`、`SESSION_TOKEN`、`DISCORD_TOKEN`）。建议统一使用 JSON 格式。

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源，仅供学习交流使用。使用前请确保遵守 [bot‑hosting.net](https://bot‑hosting.net) 的服务条款。

---

**Happy Renewing! 🎉**

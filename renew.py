#!/usr/bin/env python3

import os, re, sys, time, requests
from seleniumbase import SB

# 环境变量（必须通过 GitHub Secrets 或本地环境变量设置）
EMAIL = os.environ.get("EMAIL") or ""
PASSWORD = os.environ.get("PASSWORD") or ""
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN") or ""
TG_CHAT_ID = os.environ.get("TG_CHAT_ID") or ""
PROXY_SERVER = os.environ.get("PROXY_SERVER") or ""   # 例如 socks5://127.0.0.1:1080

BASE_URL = "https://client.therose.cloud/login"

# 检查必要变量
if not EMAIL or not PASSWORD:
    print("❌ 请设置环境变量 EMAIL 和 PASSWORD")
    sys.exit(1)

# 辅助：保存带步骤名的截图
def screenshot_step(sb, step_name):
    timestamp = int(time.time() * 1000)
    filename = f"step_{step_name}_{timestamp}.png"
    sb.save_screenshot(filename)
    print(f"📸 截图已保存: {filename}")

# 点击续期按钮
def click_extend_button(sb):
    selectors = [
        'span:contains("Extend")',
        'button:contains(title="Extend")',
    ]
    for sel in selectors:
        try:
            if sb.find_element(sel, timeout=2):
                print(f"✅ 找到按钮，选择器: {sel}")
                sb.uc_click(sel, timeout=5)
                print("✅ 点击成功")
                return True, {}
        except:
            continue
    try:
        btn = sb.find_element('button:contains("Extend")', timeout=2)
        sb.driver.execute_script("arguments[0].click();", btn)
        print("✅ 通过 JavaScript 点击成功")
        return True, {}
    except Exception as e:
        return False, {"error": str(e)}

# 检查续期是否成功
def check_renewal_success(sb):
    success_selectors = [
        '.alert-success',
        '.alert.alert-success',
        'div[role="alert"].alert-success',
        'div.alert-success',
        'span:contains("successfully purchased")',
        'div:contains("successfully purchased")'
    ]
    print("⏳ 等待5秒检查续期结果...")
    time.sleep(5)
    for selector in success_selectors:
        try:
            element = sb.find_element(selector, timeout=2)
            if element:
                text = element.text
                print(f"✅ 发现成功提示！选择器: {selector}")
                print(f"📝 提示内容: {text}")
                return True, text
        except:
            continue
    try:
        page_source = sb.get_page_source()
        if "successfully purchased" in page_source.lower():
            print("✅ 页面源码中发现 'successfully purchased' 关键词")
            return True, "服务器已成功续期"
    except:
        pass
    return False, "未检测到续期成功提示"

# 发送tg通知
def send_tg(token, chat_id, message):
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
        if resp.status_code == 200:
            print("📨 Telegram 通知已发送")
        else:
            print(f"❌ Telegram 发送失败: {resp.text}")
    except Exception as e:
        print(f"❌ Telegram 发送异常: {e}")

# 获取服务器有效期
def get_expiry(sb):
    xpath = '/html/body/div[1]/section/div/div[1]/div[2]/div/div/div/div[2]/div[2]/div[2]/div/span'
    try:
        sb.open("https://client.therose.cloud/panel?routeName=servers")
        sb.sleep(3)
        el = sb.find_element(f"xpath={xpath}", timeout=10)
        if el:
            text = el.text.strip()
            print(f"📅 服务器有效期: {text}")
            return text
    except Exception as e:
        print(f"⚠️ 获取有效期失败: {e}")
    return "未知"

# 登录流程（每步截图）
def login(sb, email, password):
    print("🌐 打开登录页面...")
    sb.open(BASE_URL)
    sb.wait_for_ready_state_complete()
    screenshot_step(sb, "1_page_loaded")

    print("📧 填写邮箱...")
    sb.type('#login_form_email', email, timeout=10)
    screenshot_step(sb, "2_email_filled")

    print("🔑 填写密码...")
    sb.type('#login_form_password', password, timeout=10)
    screenshot_step(sb, "3_password_filled")

    time.sleep(1)
    print("🛡 处理 Turnstile...")
    try:
        sb.uc_gui_click_captcha()
        print("✅ Turnstile 验证已处理")
    except Exception as e:
        print(f"⚠️ uc_gui_click_captcha 执行异常: {e}")
    screenshot_step(sb, "4_captcha_handled")

    print("🔑 点击登录按钮...")
    sb.uc_click('button:contains("Sign in")')
    screenshot_step(sb, "5_login_clicked")

    sb.sleep(3)
    for i in range(30):
        current_url = sb.get_current_url()
        page_title = sb.get_title() or ""
        print(f"📄 当前 URL: {current_url} | Title: {page_title}")
        if "panel" in current_url:
            print("✅ 登录成功，已跳转到 Dashboard")
            screenshot_step(sb, "6_login_success")
            return True, current_url
        time.sleep(1)

    print(f"❌ 登录失败，当前 URL: {sb.get_current_url()}")
    screenshot_step(sb, "6_login_failed")
    sb.save_screenshot("login_failed.png")
    return False, sb.get_current_url()

# 主流程
def main():
    print("🚀 启动浏览器")
    if PROXY_SERVER:
        print(f"🔗 使用代理: {PROXY_SERVER}")
    else:
        print("🍭 未使用代理，直连访问")

    with SB(uc=True, headless=False, proxy=PROXY_SERVER or None) as sb:
        success, url = login(sb, EMAIL, PASSWORD)

        if not success:
            msg = f"❌ 登录失败"
            print(msg)
            send_tg(TG_BOT_TOKEN, TG_CHAT_ID, msg)
            return

        # 登录成功后打开服务器列表页面
        print("🌐 打开服务器列表页面...")
        sb.open("https://client.therose.cloud/panel?routeName=servers")
        sb.sleep(3)
        screenshot_step(sb, "7_server_list")

        expiry = get_expiry(sb)
        print(f"📅 当前有效期: {expiry}")

        print("📄 开始续期流程...")
        ok, info = click_extend_button(sb)
        if not ok:
            msg = f"❌ 点击 Extend 按钮失败: {info.get('error')}"
            print(msg)
            send_tg(TG_BOT_TOKEN, TG_CHAT_ID, msg)
            return

        time.sleep(1)
        screenshot_step(sb, "8_extend_clicked")

        try:
            button = sb.find_element('button:contains("Order now")', timeout=5)
            if button:
                print("🛒 点击 Order now 按钮...")
                sb.uc_click('button:contains("Order now")')
                print("✅ 已点击 Order now 按钮")
                screenshot_step(sb, "9_ordernow_clicked")
            else:
                msg = "❌ 未找到 Order now 按钮"
                print(msg)
                send_tg(TG_BOT_TOKEN, TG_CHAT_ID, msg)
                return
        except Exception as e:
            msg = f"❌ 点击 Order now 失败: {e}"
            print(msg)
            send_tg(TG_BOT_TOKEN, TG_CHAT_ID, msg)
            return

        print("🔍 检查续期结果...")
        renewal_success, renewal_msg = check_renewal_success(sb)
        screenshot_step(sb, "10_renewal_result")

        if renewal_success:
            msg = f"✅ 续期成功！{renewal_msg}\n📅 有效期: {expiry}"
            print(msg)
            sb.save_screenshot("renewal_success.png")
        else:
            msg = f"❌ 续期可能失败: {renewal_msg}\n📅 有效期: {expiry}"
            print(msg)
            sb.save_screenshot("renewal_failed.png")

        send_tg(TG_BOT_TOKEN, TG_CHAT_ID, msg)

    print("🏁 脚本执行完毕")

if __name__ == "__main__":
    main()

def process_account(account, idx):
    email = account.get("email", f"账号{idx+1}")
    session_token = account.get("session_token", "")
    discord_token = account.get("discord_token", "")
    secret_name = account.get("secret_name", None) or ("SESSION_TOKEN" if idx == 0 else f"SESSION_TOKEN_{idx}")

    if not session_token and not discord_token:
        print(f"⚠️ 账号 {email} 缺少 Token，跳过")
        return

    sb_kwargs = {
        "uc": True,
        "headless": HEADLESS,
        "page_load_strategy": "eager",
        "agent": DEFAULT_UA,
    }
    if IS_PROXY:
        print(f"🔗 挂载代理: {PROXY_SERVER[:50]}...")
        sb_kwargs["proxy"] = PROXY_SERVER
    else:
        print("🍭 未使用代理，直连访问")

    login_method = "SESSION_TOKEN"
    with SB(**sb_kwargs) as sb:
        try:
            sb.set_page_load_timeout(30)
            sb.set_script_timeout(30)
        except:
            pass

        ip = get_current_ip(PROXY_SERVER if IS_PROXY else "")
        print(f"📍 当前出口IP: {ip}")

        # ---------- 登录 ----------
        login_ok = False
        if session_token:
            print("🚀 启动浏览器...")
            page_loaded = False
            for attempt in range(1, 4):
                try:
                    sb.open("https://bot-hosting.net/")
                    sb.wait_for_ready_state_complete()
                    sb.sleep(2)
                    current_url = sb.get_current_url()
                    if "bot-hosting.net" in current_url:
                        print(f"✅ 页面加载成功，域: bot-hosting.net (尝试 {attempt})")
                        page_loaded = True
                        break
                    else:
                        print(f"⚠️ 页面域不正确，当前 URL: {current_url}，重试 {attempt}/3")
                        sb.refresh()
                        sb.sleep(2)
                except Exception as e:
                    print(f"⚠️ 加载页面异常 (尝试 {attempt}): {e}")
                    time.sleep(3)

            if not page_loaded:
                print("❌ 无法加载 bot-hosting.net，请检查代理或网络")
                send_telegram_message(
                    format_notification("❌ 登录失败", email, login_method, error="无法加载 bot-hosting.net")
                )
                return

            current_url = sb.get_current_url()
            if "bot-hosting.net" not in current_url:
                print(f"❌ 当前域不是 bot-hosting.net，当前 URL: {current_url}")
                send_telegram_message(
                    format_notification("❌ 登录失败", email, login_method, error="域不匹配")
                )
                return

            print("📝 注入 Cookie...")
            for name, value in {"session_token": session_token, "login": "true", "theme": "system"}.items():
                if not value:
                    continue
                try:
                    sb.add_cookie({"name": name, "value": value})
                except Exception as e:
                    print(f"⚠️ 添加 Cookie {name} 失败: {e}")
                    try:
                        sb.open("https://bot-hosting.net/")
                        sb.wait_for_ready_state_complete()
                        sb.sleep(2)
                        sb.add_cookie({"name": name, "value": value})
                    except Exception as e2:
                        print(f"❌ 第二次添加 Cookie {name} 仍然失败: {e2}")
                        send_telegram_message(
                            format_notification("❌ 登录失败", email, login_method, error="Cookie 注入失败")
                        )
                        return

            print("🌐 访问 https://bot-hosting.net/a/billings ...")
            try:
                sb.open("https://bot-hosting.net/a/billings")
                sb.wait_for_ready_state_complete()
                sb.sleep(3)
                current_url = sb.get_current_url()
                if "/a/billings" in current_url and "/login" not in current_url:
                    login_ok = True
                    print("✅ SESSION_TOKEN 登录成功")
                else:
                    print(f"❌ SESSION_TOKEN 登录失败，当前URL: {current_url}")
            except Exception as e:
                print(f"❌ 访问账单页异常: {e}")
                send_telegram_message(
                    format_notification("❌ 登录失败", email, login_method, error="访问账单页失败")
                )
                return

        if not login_ok and discord_token:
            login_method = "Discord Token"
            print("\n🔄 尝试 Discord OAuth 登录...")
            if do_discord_login(sb, discord_token):
                try:
                    print("🌐 访问 https://bot-hosting.net/a/billings ...")
                    sb.open("https://bot-hosting.net/a/billings")
                    sb.wait_for_ready_state_complete()
                    sb.sleep(3)
                    if "/a/billings" in sb.get_current_url():
                        login_ok = True
                        print("✅ Discord OAuth 登录成功")
                    else:
                        print("❌ Discord OAuth 后未到达账单页")
                except Exception as e:
                    print(f"❌ Discord OAuth 后访问账单页异常: {e}")
            else:
                print("❌ Discord OAuth 登录流程失败")

        if not login_ok:
            send_telegram_message(format_notification("❌ 登录失败", email, login_method, error="登录失败"))
            return

        # ---------- 获取当前到期日期 ----------
        try:
            sb.sleep(2)
            page_source = sb.get_page_source()
            current_expiry = extract_expiry_date(page_source)
            if current_expiry:
                print(f"📅 当前到期日期: {current_expiry}")
            else:
                print("⚠️ 未能提取当前到期日期")
        except:
            current_expiry = None
            print("⚠️ 获取页面源码失败")

        # ---------- 查找外部续期按钮 ----------
        outer_renew_selector = None
        countdown_text = None
        xpath_selectors = [
            '/html/body/div/div[1]/div[3]/main/div/div/section[1]/div[3]/div/button[1]',
            '//button[contains(text(),"Renew free plan")]',
            '//a[contains(text(),"Renew free plan")]',
            '//button[contains(text(),"Renew")]',
            '//a[contains(text(),"Renew")]',
            '//*[contains(@class,"renew") and contains(text(),"Renew")]',
        ]
        for xp in xpath_selectors:
            try:
                if sb.is_element_visible(xp):
                    button_text = sb.get_text(xp)
                    if "Renew in" in button_text:
                        match = re.search(r"Renew in (\d{2}:\d{2}:\d{2})", button_text)
                        if match:
                            countdown_text = match.group(1)
                        break
                    elif "Renew" in button_text and "in" not in button_text.lower():
                        outer_renew_selector = xp
                        print(f"✅ 续期按钮可用: '{button_text}' (XPath: {xp})")
                        break
            except:
                pass

        if not outer_renew_selector:
            if countdown_text:
                friendly = format_countdown(countdown_text)
                print(f"⏳ 未到续期时间，倒计时: {countdown_text} ({friendly})")
                send_telegram_message(
                    format_notification("⏳ 未到续期时间", email, login_method,
                                       extra=f"⏱️ 可续期时间: {friendly}后",
                                       expiry_date=current_expiry or "（未获取到）")
                )
            else:
                print("ℹ️ 未找到续期按钮或倒计时，状态未知")
                send_telegram_message(format_notification("ℹ️ 无需续期", email, login_method, extra="状态未知，请手动检查"))
            new_token, _ = get_cookie_info(sb, "session_token")
            if new_token and new_token != session_token and GH_TOKEN:
                update_github_secret(secret_name, new_token)
            print(f"🏁 账号 {email} 处理完毕")
            return

        # ---------- 执行续期 ----------
        renew_success = False
        max_attempts = 3  # 增加重试次数
        for attempt in range(1, max_attempts + 1):
            if renew_success:
                break
            print(f"🔄 续期尝试 {attempt}/{max_attempts}")
            try:
                # 检查浏览器是否存活
                try:
                    sb.get_current_url()
                except:
                    print("❌ 浏览器会话已失效，跳过该账号")
                    sb.save_screenshot(f"browser_crash_{email}_{int(time.time())}.png")
                    send_telegram_message(
                        format_notification("❌ 续期失败", email, login_method, error="浏览器崩溃")
                    )
                    return

                # 点击外部续期按钮
                print("🔄 点击外部续期按钮，等待验证窗口...")
                sb.click(outer_renew_selector)
                sb.sleep(5)
                sb.save_screenshot(f"after_click_renew_{email}_{int(time.time())}.png")

                # ---------- Turnstile 处理（增强版） ----------
                print("🔒 处理 Turnstile 验证...")
                modal_selector = '.modal, .overlay, [role="dialog"], .challenge-modal, .popup, .dialog'
                # 等待模态框出现
                for _ in range(15):
                    try:
                        if sb.is_element_visible(modal_selector, timeout=1):
                            break
                    except:
                        pass
                    time.sleep(1)

                # 尝试使用 uc_gui_handle_cf 或 uc_gui_click_captcha
                try:
                    # 优先使用 handle_cf (更全面)
                    sb.uc_gui_handle_cf()
                    print("✅ Turnstile 已处理 (uc_gui_handle_cf)")
                except Exception as e:
                    print(f"⚠️ uc_gui_handle_cf 失败: {e}，尝试 uc_gui_click_captcha")
                    try:
                        sb.uc_gui_click_captcha()
                        print("✅ Turnstile 点击已触发 (uc_gui_click_captcha)")
                    except Exception as e2:
                        print(f"⚠️ uc_gui_click_captcha 也失败: {e2}")

                # 等待验证完成（检测模态框消失或出现成功标志）
                print("⏳ 等待 Turnstile 验证完成...")
                for i in range(30):  # 最多等待30秒
                    try:
                        # 如果模态框消失，说明验证可能已完成
                        if not sb.is_element_visible(modal_selector, timeout=0.5):
                            print("✅ 模态框已消失，验证可能完成")
                            break
                        # 检查是否有错误提示
                        if sb.is_element_visible('[class*="error"]', timeout=0.5):
                            print("⚠️ 检测到验证错误，可能失败")
                            break
                    except:
                        pass
                    time.sleep(1)
                else:
                    print("⚠️ 验证超时，但继续尝试")

                # 等待一小段时间让页面稳定
                time.sleep(3)

                # ---------- 点击模态框内续期按钮 ----------
                print("⏳ 查找模态框内的续期按钮...")
                renew_btn_selectors = [
                    '//button[contains(text(),"Renew for 4 days")]',
                    '//button[contains(text(),"Renew free plan")]',
                    '//button[contains(text(),"Renew")]',
                    'button[data-action="renew"]',
                    '.modal button:contains("Renew")',
                ]
                clicked = False
                for selector in renew_btn_selectors:
                    try:
                        sb.wait_for_element_visible(selector, timeout=8)
                        sb.click(selector)
                        clicked = True
                        print(f"✅ 已点击续期按钮: {selector}")
                        sb.save_screenshot(f"clicked_renew_button_{email}_{int(time.time())}.png")
                        break
                    except Exception as e:
                        print(f"⚠️ 尝试选择器 {selector} 失败: {e}")
                if not clicked:
                    print("❌ 未找到续期按钮，可能弹窗未正确加载")
                    sb.save_screenshot(f"renew_button_not_found_{email}_{int(time.time())}.png")
                    # 尝试强制关闭模态框并重试
                    try:
                        sb.driver.execute_script("""
                            var modal = document.querySelector('.modal, .overlay, [role="dialog"]');
                            if (modal) modal.style.display = 'none';
                        """)
                    except:
                        pass
                    continue

                # ---------- 等待续期完成 ----------
                print("⏳ 等待续期完成（30秒）...")
                time.sleep(30)

                # 刷新账单页，检查到期日期
                sb.open("https://bot-hosting.net/a/billings")
                sb.wait_for_ready_state_complete()
                time.sleep(8)

                new_page_text = sb.get_page_source()
                new_expiry = extract_expiry_date(new_page_text)
                new_match = re.search(r"Renew in (\d{2}:\d{2}:\d{2})", new_page_text)

                if new_expiry and new_expiry != current_expiry:
                    print(f"✅ 续期成功！到期日期已更新为: {new_expiry}")
                    send_telegram_message(
                        format_notification("✅ 续期成功", email, login_method, extra="到期日期已更新", expiry_date=new_expiry)
                    )
                    renew_success = True
                    break
                elif new_match:
                    new_countdown = new_match.group(1)
                    print(f"✅ 续期成功！新的倒计时: {new_countdown}")
                    send_telegram_message(
                        format_notification(
                            "✅ 续期成功", email, login_method,
                            extra=f"⏱️ 可续期时间: {format_countdown(new_countdown)}后",
                            expiry_date=new_expiry or "（未获取到）"
                        )
                    )
                    renew_success = True
                    break
                else:
                    print("⚠️ 续期结果未知，到期日期未变化")
                    sb.save_screenshot(f"renew_unknown_{email}_{int(time.time())}.png")
                    # 尝试再刷新一次
                    sb.sleep(5)
                    sb.open("https://bot-hosting.net/a/billings")
                    sb.wait_for_ready_state_complete()
                    time.sleep(5)
                    new_page_text = sb.get_page_source()
                    new_expiry = extract_expiry_date(new_page_text)
                    if new_expiry and new_expiry != current_expiry:
                        print(f"✅ 续期成功（延迟），到期日期已更新为: {new_expiry}")
                        send_telegram_message(
                            format_notification("✅ 续期成功", email, login_method, extra="到期日期已更新", expiry_date=new_expiry)
                        )
                        renew_success = True
                        break
                    else:
                        print("❌ 续期失败，准备重试")
                        # 尝试关闭模态框并重试
                        try:
                            sb.driver.execute_script("""
                                var modal = document.querySelector('.modal, .overlay, [role="dialog"]');
                                if (modal) modal.style.display = 'none';
                            """)
                        except:
                            pass
                        # 刷新页面重置状态
                        sb.open("https://bot-hosting.net/a/billings")
                        sb.wait_for_ready_state_complete()
                        time.sleep(3)
                        continue
            except Exception as e:
                print(f"⚠️ 续期流程异常: {e}")
                sb.save_screenshot(f"exception_{email}_{int(time.time())}.png")
                if "Connection refused" in str(e) or "ERR_CONNECTION_REFUSED" in str(e):
                    print("❌ 浏览器会话崩溃，跳过该账号")
                    send_telegram_message(
                        format_notification("❌ 续期失败", email, login_method, error="浏览器崩溃")
                    )
                    return
                try:
                    sb.open("https://bot-hosting.net/a/billings")
                    sb.wait_for_ready_state_complete()
                    time.sleep(3)
                except:
                    pass
                continue

        if not renew_success:
            print("❌ 所有续期尝试均失败，请手动检查")
            send_telegram_message(format_notification("❌ 续期失败", email, login_method, error="多次尝试后仍未成功"))

        # ---------- 更新 SESSION_TOKEN ----------
        print("🔄 检查 SESSION_TOKEN 是否需要更新")
        new_token, token_expiry = get_cookie_info(sb, "session_token")
        if should_update_cookie(new_token, session_token, token_expiry):
            if GH_TOKEN:
                if update_github_secret(secret_name, new_token):
                    print(f"✅ {secret_name} 更新成功")
                else:
                    print(f"⚠️ 更新 {secret_name} 失败")
            else:
                print("⚠️ 未设置 GH_TOKEN，无法自动更新")
                print(f"📋 请手动设置 {secret_name} = {new_token[:4]}...{new_token[-4:]}")
        else:
            print("✅ SESSION_TOKEN 无需更新")

        print(f"🏁 账号 {email} 处理完毕")

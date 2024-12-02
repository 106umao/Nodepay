import asyncio
import aiohttp
import time
import uuid
import sys
import os

from curl_cffi import requests
from loguru import logger
from colorama import Fore, Style, init
from fake_useragent import UserAgent

# 初始化colorama以支持Windows系统
init(autoreset=True)

# 配置logger，只显示INFO级别以上的日志
logger.remove()
logger.add(sys.stderr, format="{time} {level} - {message}", level="INFO", colorize=True)

def clear_screen():
    # Clear the screen based on the operating system
    if os.name == 'posix':
        os.system('clear')
    elif os.name == 'nt':
        os.system('cls')
    else:
        print("\n" * 100)  # Fallback: Print 100 new lines

def show_warning():
    confirm = input(f"{Fore.YELLOW}多账户NODEPAY机器人 \n\n请确保您有:\n1. 包含您Nodepay令牌的token.txt文件（每行一个）\n2. 包含您的代理列表的proxy.txt文件\n注意：每个令牌最多将获得3个代理\n\n按Enter键继续或按Ctrl+C取消... {Style.RESET_ALL}")

    if confirm.strip() == "":
        print(f"{Fore.GREEN}继续...{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}退出...{Style.RESET_ALL}")
        exit()

def display_menu():
    print(f"\n请选择一个选项:")
    print(f"{Fore.GREEN}1. 启动节点{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}2. 注册账户{Style.RESET_ALL}")
    choice = input(f"{Fore.CYAN}输入选项编号: {Style.RESET_ALL}")
    return choice

def register_accounts():
    print(f"{Fore.MAGENTA}注册账户功能尚未实现。{Style.RESET_ALL}")

# 常量
PING_INTERVAL = 60
RETRIES = 60

DOMAIN_API = {
    "SESSION": "http://api.nodepay.ai/api/auth/session",
    "PING": "https://nw.nodepay.org/api/network/ping"
}

CONNECTION_STATES = {
    "已连接": 1,
    "已断开": 2,
    "无连接": 3
}

status_connect = CONNECTION_STATES["无连接"]
browser_id = None
account_info = {}
last_ping_time = {}

def uuidv4():
    return str(uuid.uuid4())

def valid_resp(resp):
    if not resp or "code" not in resp or resp["code"] < 0:
        raise ValueError("无效的响应")
    return resp

async def render_profile_info(proxy, token):
    global browser_id, account_info

    try:
        np_session_info = load_session_info(proxy)

        if not np_session_info:
            # 生成新的浏览器ID
            browser_id = uuidv4()
            response = await call_api(DOMAIN_API["SESSION"], {}, proxy, token)
            valid_resp(response)
            account_info = response["data"]
            if account_info.get("uid"):
                save_session_info(proxy, account_info)
                await start_ping(proxy, token)
            else:
                handle_logout(proxy)
        else:
            account_info = np_session_info
            await start_ping(proxy, token)
    except Exception as e:
        # No error logging here
        remove_proxy_from_list(proxy)
        return None

async def call_api(url, data, proxy, token):
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
    random_user_agent = user_agent.random
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": random_user_agent,
        "Content-Type": "application/json",
        "Origin": "chrome-extension://lgmpfmgeabnnlemejacfljbmonaomfmm",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        response = requests.post(url, json=data, headers=headers, impersonate="chrome110", proxies={
                                "http": proxy, "https": proxy}, timeout=30)

        response.raise_for_status()
        return valid_resp(response.json())
    except Exception as e:
        # No error logging here
        pass

async def start_ping(proxy, token):
    try:
        while True:
            await ping(proxy, token)
            await asyncio.sleep(PING_INTERVAL)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        # No error logging here
        pass

async def ping(proxy, token):
    global last_ping_time, RETRIES, status_connect

    current_time = time.time()

    if proxy in last_ping_time and (current_time - last_ping_time[proxy]) < PING_INTERVAL:
        return

    last_ping_time[proxy] = current_time

    try:
        data = {
            "id": account_info.get("uid"),
            "browser_id": browser_id,
            "timestamp": int(time.time()),
            "version": "2.2.7"
        }

        response = await call_api(DOMAIN_API["PING"], data, proxy, token)
        if response["code"] == 0:
            # 将IP分数翻译成中文
            ip_score = response["data"].get("ip_score", "未知")
            if isinstance(ip_score, (int, float)):
                ip_score_chinese = f"{Fore.GREEN}IP分数: {ip_score}{Style.RESET_ALL}"
            else:
                ip_score_chinese = f"{Fore.YELLOW}IP分数: {ip_score}（非数值）{Style.RESET_ALL}"
            
            logger.info(f"{Fore.CYAN}Ping成功，代理 {proxy}，{ip_score_chinese}{Style.RESET_ALL}")
            RETRIES = 0
            status_connect = CONNECTION_STATES["已连接"]
    except Exception as e:
        # No error logging here
        pass

def handle_ping_fail(proxy, response):
    # No error logging here
    pass

def handle_logout(proxy):
    # No error logging here
    pass

def load_proxies(proxy_file):
    try:
        with open(proxy_file, 'r') as file:
            proxies = file.read().splitlines()
        return proxies
    except Exception as e:
        # No error logging here
        raise SystemExit(f"{Fore.RED}由于加载代理失败，程序退出。{Style.RESET_ALL}")

def load_tokens(token_file):
    try:
        with open(token_file, 'r') as file:
            tokens = file.read().splitlines()
        return tokens
    except Exception as e:
        # No error logging here
        raise SystemExit(f"{Fore.RED}由于加载令牌失败，程序退出。{Style.RESET_ALL}")

def save_status(proxy, status):
    pass

def save_session_info(proxy, data):
    data_to_save = {
        "uid": data.get("uid"),
        "browser_id": browser_id
    }
    pass

def load_session_info(proxy):
    return {}

def is_valid_proxy(proxy):
    return True

def remove_proxy_from_list(proxy):
    pass

async def main():
    clear_screen()  # Clear the screen before starting the script
    all_proxies = load_proxies('proxy.txt')  # 从文件中加载代理
    all_tokens = load_tokens('token.txt')  # 从令牌列表中加载令牌

    if not all_tokens:
        print(f"{Fore.RED}在token.txt中未找到令牌。程序退出。{Style.RESET_ALL}")
        exit()

    while True:
        choice = display_menu()
        
        if choice == "1":
            print(f"{Fore.GREEN}启动节点...{Style.RESET_ALL}")
            while True:
                for token in all_tokens:
                    active_proxies = [
                        proxy for proxy in all_proxies if is_valid_proxy(proxy)][:100]
                    tasks = {asyncio.create_task(render_profile_info(
                        proxy, token)): proxy for proxy in active_proxies}

                    done, pending = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        failed_proxy = tasks[task]
                        if task.result() is None:
                            active_proxies.remove(failed_proxy)
                            if all_proxies:
                                new_proxy = all_proxies.pop(0)
                                if is_valid_proxy(new_proxy):
                                    active_proxies.append(new_proxy)
                                    new_task = asyncio.create_task(
                                        render_profile_info(new_proxy, token))
                                    tasks[new_task] = new_proxy
                    tasks.pop(task)

                    for proxy in set(active_proxies) - set(tasks.values()):
                        new_task = asyncio.create_task(
                            render_profile_info(proxy, token))
                        tasks[new_task] = proxy
                    await asyncio.sleep(3)
                await asyncio.sleep(10)
        elif choice == "2":
            register_accounts()
        else:
            print(f"{Fore.RED}无效的选项。请选择1或2。{Style.RESET_ALL}")

if __name__ == '__main__':
    show_warning()
    print(f"\n{Fore.GREEN}现在运行...{Style.RESET_ALL}")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        # No error logging here
        exit()

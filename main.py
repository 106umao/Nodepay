import asyncio
import time
import uuid
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

from curl_cffi import requests
from loguru import logger
from colorama import Fore, Style, init
from fake_useragent import UserAgent

# 初始化colorama
init(autoreset=True)

# 配置logger，只显示INFO级别以上的日志
logger.remove()
logger.add(sys.stderr, format="{time} {level} - {message}", level="INFO", colorize=True)

# 常量定义
PING_INTERVAL = 60
MAX_RETRIES = 3
VERSION = "2.2.7"

DOMAIN_API = {
    "SESSION": "http://api.nodepay.ai/api/auth/session",
    "PING": "https://nw.nodepay.org/api/network/ping",
    "LOGIN": "http://api.nodepay.ai/api/auth/login"
}

class NodePayBot:
    def __init__(self):
        self.browser_id = str(uuid.uuid4())
        self.account_info: Dict = {}
        self.last_ping_time: Dict[str, float] = {}
        self.active_proxies: List[str] = []
        self.all_tokens: List[str] = []
        self.session_file = Path("sessions.json")
        
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def show_warning(self):
        print(f"{Fore.YELLOW}多账户NODEPAY机器人\n")
        print("请确保您有:")
        print("1. 包含您Nodepay令牌的token.txt文件（每行一个）")
        print("2. 包含您的代理列表的proxy.txt文件")
        print("注意：每个令牌最多将获得3个代理\n")
        
        input(f"按Enter键继续或按Ctrl+C取消... {Style.RESET_ALL}")
        print(f"{Fore.GREEN}继续...{Style.RESET_ALL}")

    def display_menu(self) -> str:
        print(f"\n请选择一个选项:")
        print(f"{Fore.GREEN}1. 启动节点{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}2. 注册账户{Style.RESET_ALL}")
        print(f"{Fore.BLUE}3. 登录账户获取Token{Style.RESET_ALL}")
        return input(f"{Fore.CYAN}输入选项编号: {Style.RESET_ALL}")

    def load_files(self):
        try:
            with open('proxy.txt', 'r') as f:
                self.active_proxies = [line.strip() for line in f if line.strip()]
            
            with open('token.txt', 'r') as f:
                self.all_tokens = [line.strip() for line in f if line.strip()]
                
            if not self.all_tokens:
                raise ValueError("Token文件为空")
                
            if not self.active_proxies:
                raise ValueError("代理文件为空")
                
        except FileNotFoundError as e:
            logger.error(f"找不到必要的文件: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"加载文件时出错: {e}")
            sys.exit(1)

    async def call_api(self, url: str, data: dict, proxy: str, token: str) -> dict:
        user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers=['chrome']).random
        headers = {
            "Authorization": f"Bearer {token}" if token else "",
            "User-Agent": user_agent,
            "Content-Type": "application/json",
            "Origin": "chrome-extension://lgmpfmgeabnnlemejacfljbmonaomfmm",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
        }

        for _ in range(MAX_RETRIES):
            try:
                response = requests.post(
                    url,
                    json=data,
                    headers=headers,
                    impersonate="chrome110",
                    proxies={"http": proxy, "https": proxy} if proxy else None,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"API调用失败: {e}")
                await asyncio.sleep(1)
        
        raise Exception("达到最大重试次数")

    async def ping(self, proxy: str, token: str):
        current_time = time.time()
        
        if proxy in self.last_ping_time and \
           (current_time - self.last_ping_time[proxy]) < PING_INTERVAL:
            return

        self.last_ping_time[proxy] = current_time

        try:
            data = {
                "id": self.account_info.get("uid"),
                "browser_id": self.browser_id,
                "timestamp": int(time.time()),
                "version": VERSION
            }

            response = await self.call_api(DOMAIN_API["PING"], data, proxy, token)
            
            if response.get("code") == 0:
                ip_score = response["data"].get("ip_score", "未知")
                score_text = f"IP分数: {ip_score}" if isinstance(ip_score, (int, float)) \
                           else f"IP分数: {ip_score}（非数值）"
                logger.info(f"Ping成功 - 代理: {proxy} - {score_text}")
                return True
                
        except Exception as e:
            logger.error(f"Ping失败 - 代理: {proxy} - 错误: {e}")
            return False

    async def render_profile_info(self, proxy: str, token: str) -> Optional[bool]:
        try:
            response = await self.call_api(DOMAIN_API["SESSION"], {}, proxy, token)
            
            if response.get("code") == 0:
                self.account_info = response["data"]
                logger.info(f"账户信息获取成功 - 代理: {proxy}")
                return True
            
            logger.warning(f"账户信息获取失败 - 代理: {proxy}")
            return False
            
        except Exception as e:
            logger.error(f"处理账户信息时出错 - 代理: {proxy} - 错误: {e}")
            return None

    async def run_node(self, token: str, proxy: str):
        try:
            if await self.render_profile_info(proxy, token):
                while True:
                    if not await self.ping(proxy, token):
                        break
                    await asyncio.sleep(PING_INTERVAL)
        except Exception as e:
            logger.error(f"节点运行错误 - 代理: {proxy} - 错误: {e}")

    async def start_nodes(self):
        self.load_files()  # 确保文件已加载
        while True:
            tasks = []
            for token in self.all_tokens:
                for proxy in self.active_proxies[:3]:  # 每个令牌最多3个代理
                    task = asyncio.create_task(self.run_node(token, proxy))
                    tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks)
            await asyncio.sleep(10)

    async def login_account(self):
        email = input("请输入您的电子邮件: ")
        password = input("请输入您的密码: ")
        
        try:
            data = {
                "email": email,
                "password": password,
                "browser_id": self.browser_id
            }
            
            # 直接发送请求，不使用代理
            response = await self.call_api(DOMAIN_API["LOGIN"], data, None, "")
            
            if response.get("code") == 0:
                token = response["data"].get("token")
                if token:
                    with open('tokenz.txt', 'a') as file:
                        file.write(f"{token}\n")
                    logger.info(f"登录成功，Token已保存到tokenz.txt")
                else:
                    logger.warning("登录成功，但未获取到Token")
            else:
                logger.error(f"登录失败 - {response.get('message')}")
        except Exception as e:
            logger.error(f"登录时发生错误 - {e}")

    async def main(self):
        self.clear_screen()
        self.show_warning()

        while True:
            choice = self.display_menu()
            
            if choice == "1":
                print(f"{Fore.GREEN}启动节点...{Style.RESET_ALL}")
                await self.start_nodes()
            elif choice == "2":
                print(f"{Fore.YELLOW}注册账户功能尚未实现{Style.RESET_ALL}")
            elif choice == "3":
                await self.login_account()
            else:
                print(f"{Fore.RED}无效的选项，请选择1、2或3{Style.RESET_ALL}")

if __name__ == "__main__":
    bot = NodePayBot()
    try:
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}程序已停止{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"程序出错: {e}")

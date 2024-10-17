import asyncio
import os
import json
from urllib.parse import unquote
from typing import Optional, List
from halo import Halo
from colorama import init, Fore, Style

from pyrogram import Client
from pyrogram.errors import (
    AuthKeyUnregistered,
    FloodWait,
    Unauthorized,
    UserDeactivated,
)
from pyrogram.raw.functions.messages import RequestWebView

from bot.utils.logger import logger
from bot.exceptions import InvalidSession
from dotenv import load_dotenv

# 初始化 colorama
init(autoreset=True)

# Load environment variables from .env file
load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSIONS_DIR = 'sessions/'
BOT_INFO_FILE = 'bot_information.json'
DELAY = 5

banner = """

  _________                .__           __   ___________                            .___                 
 /   _____/  ____  _______ |__|______  _/  |_ \_   _____/_______   ____    ____    __| _/  ____    _____  
 \_____  \ _/ ___\ \_  __ \|  |\____ \ \   __\ |    __)  \_  __ \_/ __ \ _/ __ \  / __ |  /  _ \  /     \ 
 /        \\  \___  |  | \/|  ||  |_> > |  |   |     \    |  | \/\  ___/ \  ___/ / /_/ | (  <_> )|  Y Y  |
/_______  / \___  > |__|   |__||   __/  |__|   \___  /    |__|    \___  > \___  >\____ |  \____/ |__|_|  /
        \/      \/             |__|                \/                 \/      \/      \/               \/ 

https://t.me/+VvWAMr-nDcI1MGQ9
"""

options = """
Select an action:

    1. Create session
    2. Run bot
"""

async def get_tg_web_data(tg_client: Client, session_name: str, bot_username: str, url: str) -> str:
    try:
        if not tg_client.is_connected:
            try:
                await tg_client.connect()
            except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                raise InvalidSession(session_name)

        web_view = await tg_client.invoke(
            RequestWebView(
                peer=await tg_client.resolve_peer(bot_username),
                bot=await tg_client.resolve_peer(bot_username),
                platform='android',
                from_bot_menu=False,
                url=url
            )
        )

        auth_url = web_view.url
        tg_web_data = unquote(
            string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0])

        if tg_client.is_connected:
            await tg_client.disconnect()

        return tg_web_data

    except InvalidSession as error:
        raise error

    except Exception as error:
        logger.error(f"{session_name} | Unknown error while getting Tg Web Data: {error}")
        await asyncio.sleep(delay=3)

def read_bot_info(file_path: str) -> List[dict]:
    with open(file_path, 'r') as file:
        return json.load(file)['bots']

async def process_session(session_file: str, bot_usernames: List[str], web_bot_urls: List[str]):
    session_name = os.path.splitext(os.path.basename(session_file))[0]
    tg_client = Client(os.path.join(SESSIONS_DIR, session_name), api_id=API_ID, api_hash=API_HASH)

    for bot_username, url in zip(bot_usernames, web_bot_urls):
        spinner = Halo(text=f'Processing {session_name}', spinner='dots')
        spinner.start()
        
        try:
            tg_web_data = await get_tg_web_data(tg_client, session_name, bot_username, url)
            if tg_web_data:
                with open(f"{bot_username}_token.txt", 'a') as file:
                    file.write(f"{tg_web_data}\n")
                spinner.succeed(f"{Fore.GREEN}v Username | {session_name}")
                print(f"{Fore.CYAN}Token | {session_name} |  Successfully written to {bot_username}_token.txt")
            else:
                spinner.fail(f"Failed to retrieve tg_web_data for {bot_username}")
        except Exception as e:
            spinner.fail(f"Error processing {session_name} for {bot_username}: {str(e)}")
        
        await asyncio.sleep(DELAY)

async def main():
    if not os.path.exists(SESSIONS_DIR):
        os.makedirs(SESSIONS_DIR)

    print(Fore.CYAN + banner)
    print(Fore.YELLOW + options)

    choice = input(Fore.GREEN + "Enter your choice (1/2): " + Style.RESET_ALL).strip()
    if not choice:
        print(Fore.RED + "No input provided. Exiting...")
        return

    bot_info = read_bot_info(BOT_INFO_FILE)
    bot_usernames = [bot['username'] for bot in bot_info]
    web_bot_urls = [bot['url'] for bot in bot_info]

    if choice == '1':
        phone_number = input(Fore.GREEN + "Enter your phone number (with country code): " + Style.RESET_ALL).strip()
        session_name = input(Fore.GREEN + "Enter a name for the new session: " + Style.RESET_ALL).strip()
        tg_client = Client(os.path.join(SESSIONS_DIR, session_name), api_id=API_ID, api_hash=API_HASH, phone_number=phone_number)
        await tg_client.start()
        print(Fore.CYAN + f"New session '{session_name}' created and logged in.")
        await tg_client.stop()
    elif choice == '2':
        print(Fore.MAGENTA + "Available bots:")
        for i, bot_username in enumerate(bot_usernames, start=1):
            print(Fore.CYAN + f"{i}. {bot_username}")

        bot_choice = input(Fore.GREEN + "Select a bot by number: " + Style.RESET_ALL).strip()
        if not bot_choice:
            print(Fore.RED + "No input provided. Exiting...")
            return
        
        bot_choice = int(bot_choice) - 1
        selected_bot_usernames = [bot_usernames[bot_choice]]
        selected_web_bot_urls = [web_bot_urls[bot_choice]]

        print(f"{Fore.YELLOW}Selected bot | {selected_bot_usernames[0]}")

        session_files = [os.path.join(SESSIONS_DIR, f) for f in os.listdir(SESSIONS_DIR) if f.endswith('.session')]
        
        for session_file in session_files:
            try:
                await process_session(session_file, selected_bot_usernames, selected_web_bot_urls)
            except Exception as e:
                print(f"{Fore.RED}An error occurred while processing session {session_file}")
                print(f"{Fore.RED}Error details: {e}")
                print(f"{Fore.RED}Skipping this session.")
    else:
        print(Fore.RED + "Invalid choice. Please enter '1' or '2'.")

if __name__ == '__main__':
    asyncio.run(main())
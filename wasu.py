from discord.ext import commands
import discord
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#인텐트 설정 (권한설정)
intents = discord.Intents.default()
intents.message_content = True

#연결
bot = commands.Bot(command_prefix = "!", intents = intents)

load_dotenv()
TOKEN = os.getenv("TOKEN")

@bot.event
async def on_ready():
    activity = discord.Game(name="Wasureta 플레이")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    logging.info(f'Logged on as {bot.user}!')
    await load_cogs()

#cog 추가 (클래스 설정)
async def load_cogs():        
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                logging.info(f'{filename} : success')
            except Exception as e:
                logging.info(f'{filename} : {e}')
    await bot.tree.sync()

#봇 실행
bot.run(TOKEN)
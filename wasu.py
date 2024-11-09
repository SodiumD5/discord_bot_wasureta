from discord.ext import commands
import discord
import asyncio
import os
from dotenv import load_dotenv

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
    print(f'Logged on as {bot.user}!')
    await load_cogs()

#cog 추가 (클래스 설정)
async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'{filename} : success')
            except Exception as e:
                print(f'{filename} : {e}')

print("hi")
#봇 실행
bot.run(TOKEN)
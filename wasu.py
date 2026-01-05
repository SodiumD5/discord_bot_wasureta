from discord.ext import commands
import discord
import os
from dotenv import load_dotenv
from database.database_init import setting
from utils.error_controller import report

# ------ Main File (이 파일을 실행하여 봇을 시작한다.) ------
# 권한 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

load_dotenv()
TOKEN = os.getenv("TOKEN")


@bot.before_invoke
async def count_command(ctx):
    report.command_count += 1


@bot.event
async def on_ready():
    try:
        setting.database_init()
    except:
        print("MySQL 데이터베이스 연결 실패")

    activity = discord.Game(name="Wasureta 플레이 중...")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"Logged on as {bot.user}!")

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            if filename in ["youtube.py"]:
                continue
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"{filename} : success")
            except Exception as e:
                print(f"{filename} : {e}")

    try:
        scheduler = report.start_error_scheduler()
        print("error_controller : success")
    except KeyboardInterrupt:
        scheduler.shutdown()
    await bot.tree.sync()


# 봇 실행
bot.run(TOKEN)

from discord.ext import commands, tasks
from discord.ui import Button, View
from discord import app_commands
from collections import deque
import discord, asyncio, yt_dlp, functools, random, data.to_supabase as to_supabase, crolling, logging, time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class SWMSCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="wasu", description="wasureta를 바로 다음 곡으로 선정한다.")
    async def wasu(self, ctx):
        await ctx.defer()

    @commands.hybrid_command(name="gd", description="미상이가 좋아하는 랜덤노래 무슨 노래 재생 스타트~!")
    async def gd(self, ctx):
        await ctx.defer()


async def setup(bot):
    await bot.add_cog(SWMSCommands(bot))

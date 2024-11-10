import discord
import time
from discord.ext import commands

class basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("ping.py is ready")

    #선긋기
    @commands.command(name = "---")
    async def draw_line(self, ctx):
        """선을 그린다"""
        await ctx.message.delete()
        await ctx.channel.send(f'```ansi\n[2;34m{"-"*50}[0m\n```')

    #ping날리기
    @commands.command(name = "ping")
    async def ping_pong(self, ctx):
        """ping을 날린다"""
        start_time = time.time()
        response = await ctx.channel.send("pong", reference = ctx.message)
        end_time = time.time()
        response_time = (end_time-start_time) * 1000
        await response.edit(content = f'pong ({response_time:.2f} ms)')

async def setup(bot):
    await bot.add_cog(basic(bot))

from typing import Literal
from discord.ext import commands
from utils.music_controller import music_controller
from utils.state_checker import state_checker


# 해당명령어들은 이 봇의 아이덴티티 같은 기능으로 일반인에겐 쓸모 없다.
class SWMSCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="wasu", description="wasureta를 바로 다음 곡으로 선정한다.")
    async def wasu(self, ctx, option: Literal["원곡", "신원미상 반응"]):
        await ctx.defer()
        if await state_checker.command(ctx, type="play"):
            await music_controller.wasu(ctx, option)

    @commands.hybrid_command(name="swms", description="미상이가 좋아하는 랜덤노래 무슨 노래 재생 스타트~!")
    async def gd(self, ctx):
        await ctx.defer()
        if await state_checker.command(ctx, type="play"):
            await music_controller.swms(ctx)


async def setup(bot):
    await bot.add_cog(SWMSCommands(bot))

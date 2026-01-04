from typing import Literal
from discord.ext import commands
from discord import app_commands
from utils.forms import Form
from utils.info_controller import info_controller


# 해당 명령어들은 음성채널에 들어가 있지 않아도 쓸 순 있는 명령어이다.
class InfoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="wasureta의 명령어를 사용법을 설명해준다.")
    async def help(self, ctx):
        await ctx.defer()
        form = Form()
        await form.helper(ctx)

    @commands.hybrid_command(name="last-played", description="서버에서 가장 마지막으로 틀었던 노래의 제목과 링크를 준다.")
    async def last_played(self, ctx):
        await ctx.defer()
        await info_controller.take_last_played(ctx)

    @commands.hybrid_command(name="ranking", description="서버에서 각 멤버가 몇 번씩 재생하였는 지 순위를 알려준다.")
    async def ranking(self, ctx, 정렬기준: Literal["신청곡 수 순위", "청취 시간 순위"]):
        await ctx.defer()
        await info_controller.take_ranking(ctx, 정렬기준)

    @commands.hybrid_command(name="search-user-top10", description="한 멤버(혹은 서버)가 많이 재생한 노래의 순위를 알려준다.")
    async def find_user(self, ctx, user_name: str = None):
        await ctx.defer()

    @commands.hybrid_command(name="playlist", description="해당 멤버가 많이 틀었던 노래 플레이리스트를 랜덤으로 뽑아준다.")
    @app_commands.describe(
        user_name="누구의 플리를 찾을 지 입력 (기본 값 : 서버 전체)",
        start_num="몇 위부터 검색할 지 입력 (기본 값 : 1)",
        end_num="몇 위까지 검색할 지 입력 (기본 값 : 50)",
    )
    async def playlist(self, ctx, user_name: str = None, start_num: int = None, end_num: int = None):
        await ctx.defer()


async def setup(bot):
    await bot.add_cog(InfoCommands(bot))

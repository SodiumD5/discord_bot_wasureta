from discord.ext import commands
from discord import app_commands

from utils.music_controller import music_controller


# 해당 명령어들은 음성채널에 들어가 있지 않아도 쓸 순 있는 명령어이다. 
class InfoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ranking", description="서버에서 각 멤버가 몇 번씩 재생하였는 지 순위를 알려준다.")
    async def ranking(self, ctx):
        await ctx.defer()

    @commands.hybrid_command(name="search-server-top10", description="해당 서버에서 가장 많이 재생된 음악을을 알려준다.")
    async def rank(self, ctx):
        await ctx.defer()

    @commands.hybrid_command(name="search-user-top10", description="해당 유저의 많이 들은 노래의 순위를 알려준다.")
    async def find_user(self, ctx, user_name: str = None):
        await ctx.defer()

    @commands.hybrid_command(name="how-many-played", description="노래 제목을 입력하면, 그 노래가 해당서버에서 재생된 횟수를 알려준다.")
    async def how_many_played(self, ctx, title: str):
        await ctx.defer()

    @commands.hybrid_command(name="last-played", description="서버에서 가장 마지막으로 틀었던 노래의 제목과 링크를 준다.")
    async def last_played(self, ctx):
        await ctx.defer()
        await music_controller.take_last_played(ctx)

    @commands.hybrid_command(name="playlist", description="해당 유저가 많이 틀었던 노래 플레이리스트를 랜덤으로 뽑아준다.")
    @app_commands.describe(
        user_name="누구의 플리를 찾을 지 입력(비워두면 서버 전체에서 검색한다)",
        start_num="몇 위부터 검색할 지 입력(비워두면 1위부터 검색한다)",
        end_num="몇 위까지 검색할 지 입력(비워두면 50위까지 검색한다)",
    )
    async def playlist(self, ctx, user_name: str = None, start_num: int = None, end_num: int = None):
        await ctx.defer()


async def setup(bot):
    await bot.add_cog(InfoCommands(bot))

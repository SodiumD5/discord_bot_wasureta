from typing import Literal
from discord.ext import commands
from utils.music_controller import music_controller
from utils.state_checker import state_checker


# 해당 명령어들은 음성채널에 들어가 있지 않으면 못 쓰는 명령어들이다.
class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):  # discord.py 지정 handler
        print(f"BasicCommands 에러 : {error}")

    @commands.hybrid_command(name="play", description="유튜브 링크를 가져오면 음악을 재생한다/검색어를 입력하면 5개 중에 선택이 가능하다.")
    async def play(self, ctx, search: str):
        await ctx.defer()
        if await state_checker.command(ctx, type="play"):
            await music_controller.play(ctx, search)

    @commands.hybrid_command(name="skip", description="현재 재생 중인 음악을 스킵한다.")
    async def skip(self, ctx):
        await ctx.defer()
        if await state_checker.command(ctx, type="control"):
            await music_controller.skip(ctx)

    @commands.hybrid_command(name="pause", description="현재 재생 중인 음악을 정지하거나 재개한다.")
    async def pause(self, ctx):
        await ctx.defer()
        if await state_checker.command(ctx, type="control"):
            await music_controller.pause(ctx)

    @commands.hybrid_command(name="leave", description="wasureta를 내보낸다")
    async def leave(self, ctx):
        await ctx.defer()
        if await state_checker.command(ctx, type="control"):
            await music_controller.refresh_que(ctx, is_leave=True)

    @commands.hybrid_command(name="refresh-que", description="대기열의 모든 노래를 삭제합니다.")
    async def refresh_que(self, ctx):
        await ctx.defer()
        if await state_checker.command(ctx, type="control"):
            await music_controller.refresh_que(ctx, is_leave=False)

    @commands.hybrid_command(name="que", description="현재 재생 중인 곡 정보와 함께 현재 대기열이 몇 개의 음악이 남았는지 알려준다")
    async def left_que(self, ctx):
        await ctx.defer()
        if await state_checker.command(ctx, type="control"):
            await music_controller.que(ctx)

    @commands.hybrid_command(name="repeat", description="한 곡 반복이나, 현재플리를 반복 할 수 있습니다.")
    async def repeat(self, ctx, 반복: Literal["반복 안 함", "현재 곡 반복", "전체 반복"]):
        await ctx.defer()
        if await state_checker.command(ctx, type="control"):
            await music_controller.repeat_control(ctx, 반복)

    @commands.hybrid_command(name="jump", description="12:34와 같이 입력하여, 해당 노래를 12분 34초로 스킵할 수 있다.")
    async def jump(self, ctx, jump_to: str):
        await ctx.defer()
        if await state_checker.command(ctx, type="control"):
            await music_controller.jump(ctx, jump_to)


async def setup(bot):
    await bot.add_cog(BasicCommands(bot))

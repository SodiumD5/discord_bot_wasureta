from discord.ext import commands

class basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    #선긋기
    @commands.hybrid_command(name = "---", description = "선을 그린다")
    async def draw_line(self, ctx):
        """선을 그린다"""
        if not ctx.interaction:
            await ctx.message.delete()
        await ctx.send(f'```ansi\n[2;34m{"-"*50}[0m\n```')


    #ping날리기
    @commands.hybrid_command(name = "ping", description = "ping을 날린다")
    async def ping_pong(self, ctx):
        """ping을 날린다"""
        latency = self.bot.latency * 1000  # 초 단위 값을 밀리초로 변환
        await ctx.send(f'pong ({latency:.2f} ms)')

async def setup(bot):
    await bot.add_cog(basic(bot))

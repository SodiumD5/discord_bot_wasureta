from discord.ext import commands
from discord import app_commands
import discord
from utils.forms import Form
from utils.music_controller import music_controller
from utils.state_checker import state_checker


# 해당 명령어들은 wasureta의 개발자만 쓸 수 있는 기능이다.
class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="notice")
    @commands.is_owner()
    @app_commands.default_permissions() 
    async def notice(self, ctx, 공지범위: str, title: str, text: str):
        await ctx.defer()
        
        try:
            text = text.replace("\\n", "\n")
            form = Form(message=text, title=title)
            if 공지범위 == "현재서버":
                form.guild = ctx.guild
                success = await form.send_notice(self.bot, 공지범위)
                if success:
                    await ctx.send("공지가 전송되었습니다.")
                else:
                    await ctx.send("공지 전송에 실패했습니다.")

            elif 공지범위 == "전체서버":
                success_count, total = await form.send_notice(self.bot, 공지범위)
                await ctx.send(f"총 {total}개 서버 중 {success_count}개 서버에 공지를 전송했습니다.")
        except:
            await ctx.send("당신은 봇의 소유자가 아닙니다.")
            

    @notice.autocomplete("공지범위")
    async def notice_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = [app_commands.Choice(name=interaction.guild.name, value="현재서버"), app_commands.Choice(name="전체서버", value="전체서버")]
        return choices


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))

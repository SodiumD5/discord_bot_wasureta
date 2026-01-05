from discord.ext import commands
from database.database_insert import database_insert
from utils.stopwatch import Stopwatch


class VoiceChannelObserver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stopwatches = {}  # {member_id: Stopwatch}

    def _is_active(self, voice_state):
        if voice_state.channel is None:
            return False

        if voice_state.self_deaf or voice_state.deaf:
            return False
        return True

    async def _start_stopwatch(self, member):
        if member.bot:  # wasureta가 아닌 다른 봇 무시
            return
        if self._is_active(member.voice):
            self.stopwatches[member.id] = Stopwatch()

    async def _record_stopwatch(self, member):
        if member.bot:
            return
        if member.id in self.stopwatches:
            listen_time = round(self.stopwatches[member.id].reset())
            del self.stopwatches[member.id]
            database_insert.update_user_listen_time(member, member.guild.id, listen_time)
            print(f"{member.name}님의 활동 시간: {listen_time}초")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        bot_voice_client = member.guild.voice_client

        if member == self.bot.user:
            if before.channel is None and after.channel is not None:  # wasureta가 들어올 때
                for m in after.channel.members:
                    await self._start_stopwatch(m)
            elif before.channel is not None and after.channel is None:  # 나갈 때
                for m in before.channel.members:
                    await self._record_stopwatch(m)
            return

        # wasureta가 음성 채널에 없으면 무시
        if not bot_voice_client or not bot_voice_client.channel:
            return

        bot_channel = bot_voice_client.channel
        was_active = before.channel == bot_channel and self._is_active(before)
        now_active = after.channel == bot_channel and self._is_active(after)

        if not was_active and now_active:  # 활성
            await self._start_stopwatch(member)
        elif was_active and not now_active:  # 비활성
            await self._record_stopwatch(member)


async def setup(bot):
    await bot.add_cog(VoiceChannelObserver(bot))

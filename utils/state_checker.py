class StateChecker:
    # 버튼이 있는 경우 interaction
    async def command(self, ctx, interaction=None, type="control"):
        from utils.forms import Form

        if interaction:
            if ctx.author.name != interaction.user.name:
                await interaction.response.send_message(f"{interaction.user.mention} 다른 사용자의 명령어를 뺏지 마세요.")
                return False

        user = ctx.author.voice
        bot = ctx.voice_client

        if not user:
            form = Form("먼저 음성 채널에 들어가주세요")
            await form.smart_send(ctx)
            return False
        if not bot:
            if type == "play":
                await ctx.author.voice.channel.connect()
                return True
            else:  # control
                form = Form("먼저 재생을 시작하세요.")
                await form.smart_send(ctx)
                return False
        if user.channel != bot.channel:
            form = Form("봇과 같은 채널이 아닙니다.")
            await form.smart_send(ctx)
            return False
        return True


state_checker = StateChecker()

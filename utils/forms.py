from discord.ui import Button, View
import discord

from data.guild import Song


class Form:
    def __init__(self, message="", data=[], title=None, guild=None, player=None):
        self.data = [None] + data  # 인덱스 맞춰줌 (guild.queue객체 리스트가 들어옴)
        self.title = title
        self.message = message
        self.guild = guild
        self.player = player
        self.obj = None
        self.view = None
        self.color = 0x00FF00

    async def disable_view(self, view):
        for item in view.children:
            item.disabled = True
        await self.obj.edit(view=view)

    async def _is_interaction_user(self, ctx, interaction):
        if ctx.author.name != interaction.user.name:
            await interaction.response.send_message(f"{interaction.user.mention} 다른 유저의 명령어를 뺏지 마세요.")
            return False
        return True

    async def smart_send(self, ctx, message=None):
        if message != None:
            send_message = message
        else:
            send_message = self.message

        if ctx.interaction:
            await ctx.interaction.followup.send(send_message)
        else:
            await ctx.send(send_message, reference=ctx.message)

    async def show5_music(self, ctx, insert_pos):
        view = View(timeout=20)

        for i in range(1, len(self.data)):
            button = Button(label=f"{i}번 재생", style=discord.ButtonStyle.green)

            async def button_callback(interaction, button_index=i):
                # 한 번만 클릭되게
                if not await self._is_interaction_user(ctx=ctx, interaction=interaction):
                    return

                for item in view.children:
                    item.disabled = True
                await self.obj.edit(view=view)

                await interaction.response.send_message(f"{button_index}번 노래를 추가하는 중...")
                title = self.data[button_index]["title"]
                url = self.data[button_index]["url"]

                await self.player.append_queue(url, ctx.author)

                if not self.player.voice_client.is_playing():
                    await self.player.play_next()

                message = f"노래 제목 : {title} \n대기열 {insert_pos}번에 추가 되었습니다."
                await interaction.edit_original_response(content=message)

            button.callback = button_callback
            view.add_item(button)

        view.on_timeout = lambda: self.disable_view(view)
        self.obj = await ctx.send(embed=discord.Embed(title=self.title, description=self.message, color=self.color), view=view)

    async def _update_queue_message(self, ctx, interaction, page):
        queue_len = self.guild.get_queue_length()
        max_result = queue_len % 10 if queue_len // 10 == page else 10

        self.title = f"대기열 총 {queue_len}곡"
        new_view = await self.show_queue(ctx, page)
        await interaction.response.edit_message(
            embed=discord.Embed(title=self.title, description=self.guild.get_queue_info(page, max_result), color=self.color),
            view=new_view,
        )

    async def show_queue(self, ctx, page) -> View:
        if self.view:
            self.view.stop()

        view = View(timeout=30)
        self.view = view

        queue_len = self.guild.get_queue_length()
        max_result = queue_len % 10 if queue_len // 10 == page else 10  # 해당페이지에 항목 개수

        # 제거 버튼
        for button_idx in range(10 * page + 1, 10 * page + max_result + 1):
            remove_button = Button(label=f"{button_idx}번 제거하기", style=discord.ButtonStyle.red)

            async def remove_button_callback(interaction, page=page, idx=button_idx):
                if not await self._is_interaction_user(ctx=ctx, interaction=interaction):
                    return

                self.guild.pop_queue(pos=idx - 1)
                await self.smart_send(ctx, f"{interaction.user.display_name}가 {idx}번을 제거했습니다.")
                await self._update_queue_message(ctx, interaction, page)

            remove_button.callback = remove_button_callback
            view.add_item(remove_button)

        # 페이지 이동 버튼
        before_button = Button(label="이전 페이지", style=discord.ButtonStyle.green)
        after_button = Button(label="다음 페이지", style=discord.ButtonStyle.green)

        async def before_button_callback(interaction, page=page):
            if not await self._is_interaction_user(ctx=ctx, interaction=interaction):
                return
            await self._update_queue_message(ctx, interaction, page - 1)

        async def after_button_callback(interaction, page=page):
            if not await self._is_interaction_user(ctx=ctx, interaction=interaction):
                return
            await self._update_queue_message(ctx, interaction, page + 1)

        before_button.callback = before_button_callback
        after_button.callback = after_button_callback

        if page > 0:  # 첫 페이지가 아닐 때
            view.add_item(before_button)
        if page != self.guild.get_queue_length() // 10:  # 마지막 페이지가 아닐때
            view.add_item(after_button)

        if not self.obj:
            self.message = self.guild.get_queue_info(page, max_result) + self.message
            embed = discord.Embed(title=self.title, description=self.message, color=self.color)
            embed.set_image(url=self.guild.now_playing.thumbnail_url)
            self.obj = await ctx.send(embed=embed, view=view)

        view.on_timeout = lambda: self.disable_view(view)
        return view

    async def show_repeat(self, ctx):
        view = View(timeout=30)
        repeat_options = {"반복 안 함": discord.ButtonStyle.red, "현재 곡 반복": discord.ButtonStyle.green, "전체 반복": discord.ButtonStyle.primary}

        async def repeat_callback(interaction, state):
            if not await self._is_interaction_user(ctx=ctx, interaction=interaction):
                return
            self.guild.repeat = state
            await interaction.response.edit_message(embed=discord.Embed(title=f"{ctx.guild.name} 서버 반복 설정", description=f"현재 상태 : {state}", color=self.color), view=view)
            await interaction.followup.send("설정 되었습니다.")
            await self.disable_view(view)

        for state, style in repeat_options.items():
            if state != self.guild.repeat:
                button = Button(label=state, style=style)

                async def button_callback(inter, state=state):
                    await repeat_callback(inter, state)

                button.callback = button_callback
                view.add_item(button)

        view.on_timeout = lambda: self.disable_view(view)
        self.obj = await ctx.send(embed=discord.Embed(title=f"{ctx.guild.name} 서버 반복 설정", description=f"현재 상태 : {self.guild.repeat}", color=self.color), view=view)

    async def show_last_played(self, ctx):
        view = View(timeout=30)

        insert_button = Button(label=f"추가하기", style=discord.ButtonStyle.green)

        async def insert_button_callback(interaction):
            await self.disable_view(view)

            author_channel = ctx.author.voice
            bot_channel = ctx.guild.me.voice

            # 같은 채널인지 확인
            if author_channel and bot_channel:
                if author_channel.channel.id != bot_channel.channel.id:
                    await interaction.followup.send_message("봇과 같은 채널이 아닙니다.")
                    return
            elif not author_channel:
                await interaction.followup.send_message("먼저 음성 채널에 들어가 주세요.")
                return
            else:
                await ctx.author.voice.channel.connect()

            if not await self._is_interaction_user(ctx=ctx, interaction=interaction):
                return

            await interaction.response.send_message("노래를 추가하는 중...")
            self.player.voice_client = ctx.voice_client
            url = self.guild.last_played.youtube_url
            message = await self.player.append_queue(url, ctx.author)
            await interaction.edit_original_response(content=message)

        insert_button.callback = insert_button_callback
        view.add_item(insert_button)

        embed = discord.Embed(title=self.title, description=self.message, color=self.color)
        embed.set_image(url=self.guild.last_played.thumbnail_url)
        self.obj = await ctx.send(embed=embed, view=view)
        view.on_timeout = lambda: self.disable_view(view)

    async def basic_view(self, ctx):
        view = View()
        embed = discord.Embed(title=self.title, description=self.message, color=self.color)
        self.obj = await ctx.send(embed=embed, view=view)

    async def helper(self, ctx):
        view = View()

        self.title = "Wasureta 설명서"
        self.message += "### 🎵 기본 명령어\n"
        self.message += "**`/play`**\n 유튜브 링크(플리도 가능), 검색어를 통해서 노래를 추가한다.\n"
        self.message += "**`/skip`**\n 현재 재생 중인 음악을 스킵한다.\n"
        self.message += "**`/pause`**\n 재생을 일시정지/재시작한다.\n"
        self.message += "**`/leave`**\n 봇을 내보낸다.\n"
        self.message += "**`/refresh-que`**\n 대기열의 모든 음악을 삭제한다.\n"
        self.message += "**`/que`**\n 현재 재생 중인 노래와 대기열의 상태를 보여주고, 음악을 삭제할 수 있다.\n"
        self.message += "**`/repeat`**\n 반복 재생 모드를 전환할 수 있다.\n"
        self.message += "**`/jump`** `HH:MM:SS`\n 재생 중인 곡의 특정 시간으로 이동합니다.\n(예: `/jump 12:34` → 12분 34초로 이동)\n"
        self.message += "\n"

        self.message += "### 📊 통계 명령어\n"
        self.message += "**`/last-played`**\n 서버에서 가장 마지막으로 들었던 노래의 정보를 제공한다.\n"
        self.message += "**`/ranking` `(신청곡 수 순위) / (청취 시간 순위)`**\n 서버에서 멤버들의 신청곡 수 또는 청취 시간 순위를 제공한다.\n"
        self.message += "**`/search-user-top10` `멤버이름(기본값:서버전체)`**\n 한 멤버(미입력시:서버전체)가 많이 재생된 노래의 순위를 제공한다.\n"
        self.message += "**`/playlist` `멤버이름(기본값:서버전체)` `검색 마지막 순위(기본값:50)`**\n 서버에서 재생된 노래를 바탕으로 랜덤 플레이리스트를 만들어준다.\n"
        self.message += "\n"

        self.message += "### 📝 시그니처 명령어\n"
        self.message += "**`/wasu` `(원곡) / (신원미상 반응)`**\n wasureta원곡 또는 리엑션을 들을 수 있다.\n"
        self.message += "**`/swms`**\n 신원미상의 유튜브 영상 중 랜덤영상을 들려준다.\n"
        self.message += "\n"

        self.message += "### ➕ 부가 명령어\n"
        self.message += "**`/---`**\n 선을 그린다.\n"
        self.message += "**`/ping`**\n ping을 날린다.\n"

        embed = discord.Embed(title=self.title, description=self.message, color=self.color)
        self.obj = await ctx.send(embed=embed, view=view)

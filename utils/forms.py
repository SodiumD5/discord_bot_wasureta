from discord.ui import Button, View
import discord
from utils.state_checker import state_checker


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
        self.timeout = 30

    async def disable_view(self, view):
        for item in view.children:
            item.disabled = True
        await self.obj.edit(view=view)

    async def _insert_song_button(self, ctx, view, number_of_button):
        for i in range(1, number_of_button):
            button = Button(label=f"{i}번 재생", style=discord.ButtonStyle.green)

            async def button_callback(interaction, button_index=i):
                if not await state_checker.command(ctx, interaction, type="play"):
                    return
                await self.disable_view(view)

                await interaction.response.send_message(f"{button_index}번 노래를 추가하는 중...")
                url = self.data[button_index]["url"]

                if not self.player:
                    from utils.music_controller import music_controller

                    self.player = music_controller.get_player(ctx.guild, ctx.voice_client)
                message = await self.player.append_queue(url, ctx.author)

                if not self.player.voice_client.is_playing():
                    await self.player.play_next()
                await interaction.edit_original_response(content=message)

            button.callback = button_callback
            view.add_item(button)
        return view

    async def show_list_view(self, ctx, number_of_button):
        view = View(timeout=self.timeout)
        view = await self._insert_song_button(ctx=ctx, view=view, number_of_button=number_of_button)
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

        view = View(timeout=self.timeout)
        self.view = view

        queue_len = self.guild.get_queue_length()
        max_result = queue_len % 10 if queue_len // 10 == page else 10  # 해당페이지에 항목 개수

        # 제거 버튼
        for button_idx in range(10 * page + 1, 10 * page + max_result + 1):
            remove_button = Button(label=f"{button_idx}번 제거하기", style=discord.ButtonStyle.red)

            async def remove_button_callback(interaction, page=page, idx=button_idx):
                if not await state_checker.command(ctx, interaction, type="control"):
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
            if not await state_checker.command(ctx, interaction, type="control"):
                return
            await self._update_queue_message(ctx, interaction, page - 1)

        async def after_button_callback(interaction, page=page):
            if not await state_checker.command(ctx, interaction, type="control"):
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

    async def show_last_played(self, ctx):
        view = View(timeout=self.timeout)

        insert_button = Button(label=f"추가하기", style=discord.ButtonStyle.green)

        async def insert_button_callback(interaction):
            if not await state_checker.command(ctx, interaction, type="play"):
                return
            await self.disable_view(view)

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

    async def send_notice(self, bot, 공지범위: str):
        async def send_to_guild(guild):
            target_channel = None

            for channel in guild.text_channels:
                if "공지" in channel.name.lower() or "notice" in channel.name.lower():
                    target_channel = channel
                    break

            if not target_channel:
                target_channel = guild.text_channels[0] if guild.text_channels else None

            if target_channel:
                try:
                    await self.basic_view(target_channel)
                    return True
                except discord.Forbidden:
                    return False
            return False

        if 공지범위 == "현재서버":
            return await send_to_guild(bot.get_guild(self.guild.id))

        elif 공지범위 == "전체서버":
            success_count = 0
            for guild in bot.guilds:
                if await send_to_guild(guild):
                    success_count += 1
            return success_count, len(bot.guilds)

    async def smart_send(self, ctx, message=None):
        if message != None:
            send_message = message
        else:
            send_message = self.message

        if ctx.interaction:
            await ctx.interaction.followup.send(send_message)
        else:
            await ctx.send(send_message, reference=ctx.message)

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
        self.message += "**`/search-top10` `멤버이름(기본값:서버전체)`**\n 한 멤버(미입력시:서버전체)가 많이 재생된 노래의 순위를 제공한다.\n(단, 멤버이름은 서버별 이름이다.)\n"
        self.message += (
            "**`/playlist` `멤버이름(기본값:서버전체)` `검색 마지막 순위(기본값:100)`**\n 서버에서 재생된 노래를 바탕으로 랜덤 플레이리스트를 만들어준다.\n(단, 멤버이름은 서버별 이름이다.)\n"
        )
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

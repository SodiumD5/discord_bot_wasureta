from discord.ui import Button, View
import discord


class Form:
    def __init__(self, message, data=[], title=None, guild=None, player=None):
        self.data = [None] + data  # 인덱스 맞춰줌 (guild.queue객체 리스트가 들어옴)
        self.title = title
        self.message = message
        self.guild = guild
        self.player = player
        self.obj = None
        self.view = None

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
                for item in view.children:
                    item.disabled = True
                await self.obj.edit(view=view)

                await interaction.response.send_message(f"{button_index}번 노래가 선택되었습니다.")
                title = self.data[button_index]["title"]
                url = self.data[button_index]["url"]

                await self.player.append_queue(url, ctx.author)

                if not self.player.voice_client.is_playing():
                    await self.player.play_next()

                self.message = f"노래 제목 : {title} \n대기열 {insert_pos}번에 추가 되었습니다."
                await self.smart_send(ctx)

            button.callback = button_callback
            view.add_item(button)

        async def time_out():
            for item in view.children:
                item.disabled = True
            await self.obj.edit(view=view)

        view.on_timeout = time_out
        self.obj = await ctx.send(embed=discord.Embed(title=self.title, description=self.message), view=view)

    async def _update_queue_message(self, ctx, interaction, page):
        queue_len = self.guild.get_queue_length()
        max_result = queue_len % 10 if queue_len // 10 == page else 10

        self.title = f"대기열 총 {queue_len}곡"
        new_view = await self.show_queue(ctx, page)
        await interaction.response.edit_message(
            embed=discord.Embed(title=self.title, description=self.guild.get_queue_info(page, max_result)),
            view=new_view,
        )

    async def show_queue(self, ctx, page) -> View:
        if self.view:
            self.view.stop()

        view = View(timeout=10)
        self.view = view

        queue_len = self.guild.get_queue_length()
        max_result = queue_len % 10 if queue_len // 10 == page else 10  # 해당페이지에 항목 개수

        # 제거 버튼
        for button_idx in range(10 * page + 1, 10 * page + max_result + 1):
            remove_button = Button(label=f"{button_idx}번 제거하기", style=discord.ButtonStyle.red)

            async def remove_button_callback(interaction, page=page, idx=button_idx):
                self.guild.pop_queue(pos=idx - 1)
                await self.smart_send(ctx, f"{interaction.user.name}가 {idx}번을 제거했습니다.")
                await self._update_queue_message(ctx, interaction, page)

            remove_button.callback = remove_button_callback
            view.add_item(remove_button)

        # 페이지 이동 버튼
        before_button = Button(label="이전 페이지", style=discord.ButtonStyle.green)
        after_button = Button(label="다음 페이지", style=discord.ButtonStyle.green)

        async def before_button_callback(interaction, page=page):
            await self._update_queue_message(ctx, interaction, page - 1)

        async def after_button_callback(interaction, page=page):
            await self._update_queue_message(ctx, interaction, page + 1)

        before_button.callback = before_button_callback
        after_button.callback = after_button_callback

        if page > 0:  # 첫 페이지가 아닐 때
            view.add_item(before_button)
        if page != self.guild.get_queue_length() // 10:  # 마지막 페이지가 아닐때
            view.add_item(after_button)

        if not self.obj:
            self.message = self.guild.get_queue_info(page, max_result) + self.message
            embed = discord.Embed(title=self.title, description=self.message)
            embed.set_image(url=self.guild.now_playing.thumbnail_url)
            self.obj = await ctx.send(embed=embed, view=view)

        # timeout
        async def time_out(view):
            for item in view.children:
                item.disabled = True
            await self.obj.edit(view=view)

        view.on_timeout = lambda: time_out(view)

        return view

    async def show_repeat(self, ctx):
        view = View(timeout=30)
        repeat_options = {"반복 안 함": discord.ButtonStyle.red, "현재 곡 반복": discord.ButtonStyle.green, "전체 반복": discord.ButtonStyle.primary}

        async def disable_view(msg):
            for item in view.children:
                item.disabled = True
            await msg.edit(view=view)

        async def repeat_callback(interaction, state):
            self.guild.repeat = state
            await interaction.response.edit_message(embed=discord.Embed(title=f"{ctx.guild.name} 서버 반복 설정", description=f"현재 상태 : {state}"), view=view)
            await disable_view(message)

        for state, style in repeat_options.items():
            if state != self.guild.repeat:
                button = Button(label=state, style=style)

                async def button_callback(inter, state=state):
                    await repeat_callback(inter, state)

                button.callback = button_callback
                view.add_item(button)

        view.on_timeout = lambda: disable_view(message)
        message = await ctx.send(embed=discord.Embed(title=f"{ctx.guild.name} 서버 반복 설정", description=f"현재 상태 : {self.guild.repeat}"), view=view)

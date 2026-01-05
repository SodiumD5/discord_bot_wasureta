import asyncio
from collections import deque
import functools
import random
from utils.error_controller import error_handler
from utils.forms import Form
from utils.music_player import MusicPlayer


# 얘가 유일하게 존재해서 여러 guild를 관리함.
class MusicController:
    def __init__(self):
        self.players = {}

    def get_player(self, guild, voice_client) -> MusicPlayer:
        """길드별 플레이어 가져오기"""
        guild_id = guild.id
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(guild, voice_client)
        else:
            self.players[guild_id].voice_client = voice_client
        return self.players[guild_id]

    @error_handler(caller_name="play")
    async def play(self, ctx, search):
        """채널연결과 guild의 player로 매칭시켜서 재생"""
        player = self.get_player(ctx.guild, ctx.voice_client)

        if "https://www.youtube.com/" in search or "https://youtu.be/" in search:  # url일 경우
            if "list=" in search:  # 플레이리스트일 경우
                message = await player.append_queue(search, ctx.author, True)  # 플리일 경우 재생하는거도 포함되있음
                form = Form(message)
                await form.smart_send(ctx)
            else:  # 단곡일 경우
                message = await player.append_queue(search, ctx.author)
                form = Form(message)
                await form.smart_send(ctx)
        else:  # 검색어일 경우
            search_output, message = await player.keyword_search_youtube(query=search, max_results=5)
            form = Form(message=message, data=search_output, title=f"{search} 검색결과", guild=player.guild, player=player)
            await form.show_list_view(ctx=ctx, number_of_button=len(search_output) + 1)  # 재생하는거도 포함되있음

    @error_handler(caller_name="skip")
    async def skip(self, ctx):
        player = self.get_player(ctx.guild, ctx.voice_client)

        if player.voice_client and player.voice_client.is_playing():
            will_disconnect = player.guild.is_queue_empty() and player.guild.repeat == "반복 안 함"
            player.voice_client.stop()
            if will_disconnect:
                player.voice_client = ctx.voice_client
                form = Form("모든 노래가 재생되어, 봇이 나갔습니다.")
                await form.smart_send(ctx)
            else:
                form = Form("다음 노래가 재생됩니다.")
                await form.smart_send(ctx)
        else:
            form = Form("현재 재생 중이 아니거나, 통화방에 없습니다.")
            await form.smart_send(ctx)

    @error_handler(caller_name="pause")
    async def pause(self, ctx):
        player = self.get_player(ctx.guild, ctx.voice_client)
        if player.voice_client.is_playing():
            player.voice_client.pause()
            player.guild.now_playing.pause(pause_start=True)
            form = Form("정지하였습니다.")
            await form.smart_send(ctx)
        else:
            player.voice_client.resume()
            player.guild.now_playing.pause(pause_start=False)
            form = Form("노래를 다시 재생합니다.")
            await form.smart_send(ctx)

    @error_handler(caller_name="refresh_que")
    async def refresh_que(self, ctx, is_leave=False):  # refresh_que와 leave명령어가 사실상 같음.
        player = self.get_player(ctx.guild, ctx.voice_client)
        player.guild.queue = deque()

        if is_leave:
            message = "연결을 끊었습니다."
        else:
            message = "대기열을 초기화 했습니다."

        form = Form(message)
        await form.smart_send(ctx)
        if is_leave:
            player.voice_client.stop()
            player.voice_client = ctx.voice_client

            form = Form(message)
            await form.smart_send(ctx)

    @error_handler(caller_name="que")
    async def que(self, ctx):
        player = self.get_player(ctx.guild, ctx.voice_client)
        message = player.guild.now_playing.song_info()
        form = Form(message=message, title=f"대기열 총 {player.guild.get_queue_length()}곡", guild=player.guild, player=player)
        await form.show_queue(ctx, page=0)

    @error_handler(caller_name="repeat_control")
    async def repeat_control(self, ctx, repeat):
        player = self.get_player(ctx.guild, ctx.voice_client)

        if player.guild.repeat == repeat:
            message = "**현재 상태와 같습니다.****\n\n"
        else:
            player.guild.repeat = repeat
            message = "**변경되었습니다.**\n\n"
        message += f"**현재 상태 : {repeat}**"
        form = Form(message=message, title=f"{player.guild.name} 서버 반복 설정")
        await form.basic_view(ctx)

    async def _invalid_input(self, ctx):
        form = Form("올바른 입력이 아닙니다.")
        await form.smart_send(ctx)

    @error_handler(caller_name="jump")
    async def jump(self, ctx, jump_to: str):
        try:
            player = self.get_player(ctx.guild, ctx.voice_client)

            parts = list(map(int, jump_to.split(":")))
            if len(parts) > 3:
                await self._invalid_input(ctx)
                return

            target_time = 0
            for i in range(len(parts)):
                target_time += 60**i * (parts[-1 - i])

            message = await player.seek_to(target_time)
            form = Form(message=message)
            await form.smart_send(ctx)
        except Exception as e:
            await self._invalid_input(ctx)
            print(e)

    @error_handler(caller_name="wasu")
    async def wasu(self, ctx, option):
        player = self.get_player(ctx.guild, ctx.voice_client)
        player.FFMPEG_OPTIONS["options"] = "-vn -loglevel debug -af volume=2"  # 볼륨 키우기

        if option == "원곡":
            original_url = "https://www.youtube.com/watch?v=NaBF7qsPxWg"
            message = await player.append_queue(url=original_url, applicant=ctx.author, pos=0)
        elif option == "신원미상 반응":
            player.FFMPEG_OPTIONS["before_options"] = "-ss 54 -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"  # 54초부터가 반응임
            swms_url = "https://www.youtube.com/watch?v=Qk1wGwRE2uI"
            message = await player.append_queue(url=swms_url, applicant=ctx.author, pos=0)
            player.guild.now_playing.played_time = 54

        form = Form(message)
        await form.smart_send(ctx)
        player.reset_option()

    @error_handler(caller_name="swms")
    async def swms(self, ctx):
        swms_playlist = "https://www.youtube.com/playlist?list=UUhoPhrRvzjAz_qagqCJAAJA"
        player = self.get_player(ctx.guild, ctx.voice_client)
        player.FFMPEG_OPTIONS["options"] = "-vn -loglevel debug -af volume=2"  # 볼륨 키우기

        loop = asyncio.get_event_loop()
        youtube_info = await loop.run_in_executor(None, functools.partial(player.YDL.extract_info, swms_playlist, download=False))
        data_entries = youtube_info["entries"]
        picked_url = random.choice(data_entries)

        message = await player.append_queue(picked_url["url"], ctx.author)
        form = Form(message)
        await form.smart_send(ctx)
        player.reset_option()


music_controller = MusicController()

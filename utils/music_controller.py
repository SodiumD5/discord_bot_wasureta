import asyncio
from collections import deque
import functools, time, discord, yt_dlp
from data.guild import Guild, Song
from utils.forms import Form


# 얘는 하나의 guild의 재생을 담당함. 메세지는 리턴으로 주기
class MusicPlayer:
    def __init__(self, guild_id, voice_client):
        self.guild_id = guild_id
        self.voice_client = voice_client
        self.guild = Guild()
        self._reset_option()

    def _reset_option(self):
        self.YT_OPTIONS = {"format": "bestaudio/best", "extract_flat": "in_playlist", "ratelimit": "0", "playlistend": 20}
        self.YDL = yt_dlp.YoutubeDL(self.YT_OPTIONS)
        self.FFMPEG_OPTIONS = {"before_options": "-ss 0 -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn -loglevel debug"}

    async def append_queue(self, url, applicant, is_playlist=False):
        """노래의 정보를 추출하고 재생가능한 ffmpeg형태로 만들어서 대기열에 추가"""
        try:
            loop = asyncio.get_event_loop()
            youtube_info = await loop.run_in_executor(None, functools.partial(self.YDL.extract_info, url, download=False))

            insert_pos = self.guild.get_queue_length()
            if self.voice_client.is_playing():
                insert_pos += 1

            if is_playlist:
                # 프리미엄 영상, 비공개 영상 등은 다운 받을 수 없는데, 이걸 확인 하려면 오래걸린다. 그냥 패싱하기로 했다.
                data_entries = youtube_info["entries"]
                song_num = min(len(data_entries), 20)

                # 첫 곡 빠르게 던지기 (첫 곡이 비정상 영상이면 아쉬운 거로)
                first_youtube_url = data_entries[0]["url"]
                await self.append_queue(first_youtube_url, applicant, False)
                await self.play_next()

                # 나머지 틀기
                if song_num > 1:
                    tasks = []
                    for single_song in data_entries[1:song_num]:
                        single_youtube_url = single_song["url"]
                        task = asyncio.create_task(self.append_queue(single_youtube_url, applicant))
                        tasks.append(task)

                    await asyncio.gather(*tasks, return_exceptions=True)

                song_num = self.guild.get_queue_length() - insert_pos + 1
                message = f"{song_num}곡이 대기열 {insert_pos}번부터 {self.guild.get_queue_length()}번까지 추가 되었습니다."
                return message
            else:
                stream_url = youtube_info["url"]

                audio_source = discord.FFmpegPCMAudio(stream_url, **self.FFMPEG_OPTIONS)
                song = Song(youtube_url=url, video_info=youtube_info, audio_source=audio_source, applicant=applicant)

                self.guild.add_queue(song)
                await self.play_next()

                message = f"노래 제목 : {song.title} \n대기열 {insert_pos}번에 추가 되었습니다."
                return message
        except Exception as e:
            print(f"스킵함 : {url}\n{e}")
            return "오류가 발생했습니다."

    async def play_next(self, overwrite=False):
        if self.guild.is_queue_empty() or self.voice_client.is_playing():
            return

        song_data = self.guild.pop_queue(pos=0)
        self.guild.now_playing = song_data  # now는 시작전에 설정

        def after_playing(error):
            if error:
                print(f"재생 오류: {error}")

            if self.voice_client is None or not self.voice_client.is_connected():
                return

            if not overwrite:  # jump명령어는 큐의 맨 앞에 넣고, 다시 뽑는 거라 이걸 하면 안 됨.
                self.guild.last_played = self.guild.now_playing  # last는 플레이 후에 설정

            if self.guild.repeat != "반복 안 함":
                audio_source = discord.FFmpegPCMAudio(self.guild.now_playing.stream_url, **self.FFMPEG_OPTIONS)
                self.guild.now_playing.audio_source = audio_source
                if self.guild.repeat == "현재 곡 반복":
                    self.guild.add_queue(self.guild.now_playing, pos=0)
                elif self.guild.repeat == "전체 반복":
                    self.guild.add_queue(self.guild.now_playing, pos=-1)

            if not self.guild.is_queue_empty():
                asyncio.run_coroutine_threadsafe(self.play_next(), self.voice_client.loop)
            else:
                asyncio.run_coroutine_threadsafe(self.voice_client.disconnect(), self.voice_client.loop)

        await asyncio.sleep(0)
        song_data.start_time = time.time()
        self.voice_client.play(song_data.audio_source, after=after_playing)

    async def keyword_search_youtube(self, query, max_results=5):
        self.YT_OPTIONS = {
            "quiet": True,
            "extract_flat": True,
            "noplaylist": True,
        }
        self.YDL = yt_dlp.YoutubeDL(self.YT_OPTIONS)

        loop = asyncio.get_event_loop()
        youtube_info = await loop.run_in_executor(None, lambda: self.YDL.extract_info(f"ytsearch{max_results}:{query}", download=False))
        data_entries = youtube_info["entries"]

        search_output = [{"title": single_song["title"], "url": single_song["url"]} for single_song in data_entries]

        message = ""
        for idx in range(len(search_output)):
            message += f"{idx+1}번 검색결과 : {search_output[idx]["title"]} \n\n"

        insert_pos = self.guild.get_queue_length()
        if self.voice_client.is_playing():
            insert_pos += 1

        self._reset_option()
        return search_output, message, insert_pos

    async def seek_to(self, target_time: int):
        self.FFMPEG_OPTIONS["before_options"] = f"-ss {target_time} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

        now_playing = self.guild.now_playing
        audio_source = discord.FFmpegPCMAudio(now_playing.stream_url, **self.FFMPEG_OPTIONS)
        self.guild.now_playing.audio_source = audio_source
        self._reset_option()

        self.guild.add_queue(data=self.guild.now_playing, pos=0)
        self.voice_client.pause()
        await self.play_next(overwrite=True)
        self.guild.now_playing.jump(target_time=target_time)

        target_time_ko = self.guild.now_playing.time_to_korean(target_time)
        message = f"현재 노래를 {target_time_ko}로 건너 뜁니다."
        return message


# 얘가 유일하게 존재해서 여러 guild를 관리함.
class MusicController:
    def __init__(self):
        self.players = {}

    def get_player(self, guild_id, voice_client) -> MusicPlayer:
        """길드별 플레이어 가져오기"""
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(guild_id, voice_client)
        else:
            self.players[guild_id].voice_client = voice_client
        return self.players[guild_id]

    async def play(self, ctx, search):
        """채널연결과 guild의 player로 매칭시켜서 재생"""
        if not ctx.author.voice:
            form = Form("먼저 음성 채널에 들어가 주세요.")
            await form.smart_send(ctx)
            return

        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        elif ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.voice_client.move_to(ctx.author.voice.channel)

        player = self.get_player(ctx.guild.id, ctx.voice_client)

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
            search_output, message, insert_pos = await player.keyword_search_youtube(query=search, max_results=5)
            form = Form(message=message, data=search_output, title=f"{search} 검색결과", guild=player.guild, player=player)
            await form.show5_music(ctx, insert_pos)  # 재생하는거도 포함되있음

    async def skip(self, ctx):
        player = self.get_player(ctx.guild.id, ctx.voice_client)

        if player.voice_client and player.voice_client.is_playing():
            will_disconnect = player.guild.is_queue_empty()
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

    async def pause(self, ctx):
        player = self.get_player(ctx.guild.id, ctx.voice_client)
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

    async def refresh_que(self, ctx, is_leave=False):  # refresh_que와 leave명령어가 사실상 같음.
        player = self.get_player(ctx.guild.id, ctx.voice_client)

        if ctx.author.voice and player.voice_client and player.voice_client.is_playing():
            player.guild.queue = deque()

            if is_leave:
                message = "연결을 끊었습니다."
            else:
                message = "대기열을 초기화 했습니다."

            form = Form(message)
            await form.smart_send(ctx)

            if is_leave:
                await player.voice_client.stop()
                player.voice_client = ctx.voice_client
        else:
            if is_leave:
                message = "이미 연결이 끊어져있습니다."
            else:
                message = "먼저 음성 채널에 들어가 주세요."

            form = Form(message)
            await form.smart_send(ctx)

    async def que(self, ctx):
        player = self.get_player(ctx.guild.id, ctx.voice_client)

        if ctx.guild.voice_client and player.voice_client.is_playing():
            message = player.guild.now_playing.song_info()
            form = Form(message=message, title=f"대기열 총 {player.guild.get_queue_length()}곡", guild=player.guild, player=player)
            await form.show_queue(ctx, page=0)
        else:
            form = Form("현재 재생 중이 아닙니다.")
            await form.smart_send(ctx)

    async def repeat_control(self, ctx):
        player = self.get_player(ctx.guild.id, ctx.voice_client)

        if not (ctx.author.voice and ctx.guild.voice_client and player.voice_client.is_playing()):
            form = Form("먼저 재생을 시작하세요.")
            await form.smart_send(ctx)
        else:
            form = Form(message="", guild=player.guild)
            await form.show_repeat(ctx)

    async def _invalid_input(self, ctx):
        form = Form("올바른 입력이 아닙니다.")
        await form.smart_send(ctx)

    async def jump(self, ctx, jump_to: str):
        try:
            player = self.get_player(ctx.guild.id, ctx.voice_client)

            if not (ctx.author.voice and ctx.guild.voice_client and player.voice_client.is_playing()):
                form = Form("먼저 재생을 시작하세요.")
                await form.smart_send(ctx)
            else:
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

    async def take_last_played(self, ctx):
        player = self.get_player(ctx.guild.id, ctx.voice_client)

        try:
            message = player.guild.last_played.song_info(caller="last-played")
            form = Form(message=message, title=f"마지막 재생 곡", guild=player.guild, player=player)
            await form.show_last_played(ctx)
        except AttributeError:
            form = Form("서버에서 노래를 재생한 기록이 없습니다.")
            await form.smart_send(ctx)
        except Exception as e:
            print(e)


music_controller = MusicController()

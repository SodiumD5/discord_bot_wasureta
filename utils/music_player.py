import asyncio
import functools, time, discord, yt_dlp
from data.guild import Guild, Song
from database.database_insert import database_insert


# 얘는 하나의 guild의 재생을 담당함. 메세지는 리턴으로 주기
class MusicPlayer:
    def __init__(self, guild, voice_client):
        self.voice_client = voice_client
        self.guild = Guild(guild)
        self.reset_option()

    def reset_option(self):
        self.YT_OPTIONS = {"format": "bestaudio/best", "extract_flat": "in_playlist", "ratelimit": "0", "playlistend": 20}
        self.YDL = yt_dlp.YoutubeDL(self.YT_OPTIONS)
        self.FFMPEG_OPTIONS = {"before_options": "-ss 0 -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn -loglevel debug -af volume=1"}

    def get_insert_pos(self):
        insert_pos = self.guild.get_queue_length()
        if self.voice_client.is_playing():
            insert_pos += 1
        return insert_pos

    async def append_queue(self, url, applicant, is_playlist=False, pos=-1):
        """노래의 정보를 추출하고 재생가능한 ffmpeg형태로 만들어서 대기열에 추가"""
        try:
            loop = asyncio.get_event_loop()
            youtube_info = await loop.run_in_executor(None, functools.partial(self.YDL.extract_info, url, download=False))

            insert_pos = self.get_insert_pos()
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

                self.guild.add_queue(data=song, pos=pos)
                await self.play_next()

                if pos == 0:
                    insert_pos = 0
                    if self.voice_client.is_playing():
                        insert_pos += 1

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
                # last_play에 있는 song객체는 last-played명령어를 호출 할 때만 DB에서 업뎃해주면 됨.
                database_insert.update_server_last_play(self.guild)

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
        self.guild.now_playing.start_time = time.time()
        database_insert.record_music_played(self.guild)

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

        self.reset_option()
        return search_output, message

    async def seek_to(self, target_time: int):
        self.FFMPEG_OPTIONS["before_options"] = f"-ss {target_time} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

        now_playing = self.guild.now_playing
        audio_source = discord.FFmpegPCMAudio(now_playing.stream_url, **self.FFMPEG_OPTIONS)
        self.guild.now_playing.audio_source = audio_source
        self.reset_option()

        self.guild.add_queue(data=self.guild.now_playing, pos=0)
        self.voice_client.pause()
        await self.play_next(overwrite=True)
        self.guild.now_playing.jump(target_time=target_time)

        target_time_ko = self.guild.now_playing.time_to_korean(target_time)
        message = f"현재 노래를 {target_time_ko}로 건너 뜁니다."
        return message


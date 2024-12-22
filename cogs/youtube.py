from discord.ext import commands
from discord.ui import Button, View
from collections import deque
import discord
import asyncio
import yt_dlp
import functools
import sys, os

#최상위 디렉토리로 올라가기
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import to_mysql, youtube_api

#서버별 독립적인 데이터를 저장할 딕셔너리
server_queues = {}

def get_server_data(guild_id):
    if guild_id not in server_queues:
        server_queues[guild_id] = deque()

    return server_queues[guild_id]

#함수를 감싸줌.
def wasu_think(func): 
    @functools.wraps(func)
    async def wasu_think_wrap(*args, **kwargs):
        ctx = args[1]
        if ctx.interaction:
            await ctx.interaction.response.defer()
        return await func(*args, **kwargs)
    return wasu_think_wrap

async def smart_send(ctx, content):
    if ctx.interaction:
        await ctx.interaction.followup.send(content)
    else:
        await ctx.send(content, reference = ctx.message)

class youtube(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    yt_dl_opts = {'format': 'best', 'extract_flat' : 'in_playlist', 'ratelimit' : 0}
    ytdl = yt_dlp.YoutubeDL(yt_dl_opts)
    ffmpeg_options = {'options' : '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}

    #음악 채워주는 함수
    async def play_next(self, ctx):
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id 
        deq= get_server_data(guild_id)

        if len(deq) > 0:
            next_play = deq.popleft()
            ctx.guild.voice_client.play(next_play[0], after= lambda e: asyncio.run_coroutine_threadsafe(
                self.handle_after_callback(ctx, e), ctx.bot.loop
            ))

            #sql 넣기
            print(guild_id, next_play[2], next_play[1])
            to_mysql.add_sql(guild_id, next_play[2], next_play[1])
        else: #큐가 다 끝남 -> 리소스 줄이기 위해서 나가기
            await ctx.guild.voice_client.disconnect()


    async def handle_after_callback(self, ctx, error):
        if error:
            print(f"Playback error: {error}")
        else:
            # 다음 곡을 비동기로 재생
            await self.play_next(ctx)
    
    def sodiumd_extract_info(self, url):
        with yt_dlp.YoutubeDL(self.yt_dl_opts) as ydl:
            data = ydl.extract_info(url, download=False)
        return data

    #첫 곡을 먼저 재생 던져 놓는 함수 (이면서, 한 곡 던져두면, 그 한곡만 처리시켜주는 함수)
    async def one_song_player(self, first_song_data, applicant):
        loop = asyncio.get_event_loop()
        video_id = first_song_data['id']
        video_url = f'https://www.youtube.com/watch?v={video_id}'

        #새로 url을 만들어서 그 url을 다시 데이터로 변환시킴. 
        video_data = await loop.run_in_executor(None, self.sodiumd_extract_info, video_url)

        song = video_data['url']
        title = video_data['title']
        music_info = discord.FFmpegPCMAudio(song, executable="C:/ffmpeg/bin/ffmpeg.exe", **self.ffmpeg_options)
        return ([music_info, title, applicant])

    #남은 곡을 재생시키는 함수
    async def left_song_player(self, left_song_data, applicant, deq):
        tasks = [
            asyncio.create_task(self.one_song_player(entry, applicant))
            for entry in left_song_data
        ]
        que_datas = await asyncio.gather(*tasks)
        
        for que_data in que_datas:
            deq.append(que_data)

    async def append_music(self, ctx, url, applicant, voice_client):
        guild_id = ctx.guild.id 
        deq= get_server_data(guild_id)

        # YouTube에서 오디오 스트림 가져오기
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, self.sodiumd_extract_info, url)
        
        #플레이리스트일 때
        #'entries'가 딕셔너리에 있을 경우는 플리임.
        if 'entries' in data:
            data_entries = data['entries']
            is_playlist = min(len(data_entries), 50) #총 몇개의 노래인지(최대 50개)
            first_song = data_entries[0]
            
            #첫 곡 던져두기
            first_song_info = await self.one_song_player(first_song, applicant)
            deq.append(first_song_info)
            await self.call_executer(ctx, voice_client, is_playlist) 

            #나머지 곡 처리
            asyncio.create_task(self.left_song_player(data_entries[1:50], applicant, deq)) #최대깊이 50곡으로 제한

        #플레이리스트가 아닐 때
        else:
            is_playlist = 1 #플리가 아닐 경우 1곡임. 
            song = data['url']
            title = data['title']
            music_info = discord.FFmpegPCMAudio(song, executable="C:/ffmpeg/bin/ffmpeg.exe", **self.ffmpeg_options)
            deq.append([music_info, title, applicant]) #곡의 정보, 제목, 그 곡의 신청자이름

            await self.call_executer(ctx, voice_client, is_playlist)

    async def call_executer(self, ctx, voice_client, is_playlist):
        guild_id = ctx.guild.id 
        deq = get_server_data(guild_id)
        
        if voice_client.is_playing():
            if is_playlist == 1:
                await smart_send(ctx, f'{is_playlist}곡이 대기열 {len(deq)}번에 추가 되었습니다.')
            else:
                await smart_send(ctx, f'{is_playlist}곡이 대기열 {len(deq)}번부터 {len(deq)+is_playlist-1}번까지 추가 되었습니다.')
        else:
            if is_playlist == 1:
                await smart_send(ctx, f'{is_playlist}곡이 대기열 0번에 추가 되었습니다.')
            else:
                await smart_send(ctx, f'{is_playlist}곡이 대기열 0번부터 {len(deq)+is_playlist-1}번까지 추가 되었습니다.')

        # 음악 재생
        if not voice_client.is_playing():
            await self.play_next(ctx)

    async def play_only(self, ctx, link):
        try:
            # 음성 채널에 연결
            if ctx.author.voice: #사용자가 음성채널에 들어가 있는지. 들어가 있으면 True
                voice_client = ctx.guild.voice_client
                applicant = ctx.author.name #신청자 정보

                if not voice_client: #봇이 연결이 안되어 있을 경우, 연결시키기
                    voice_client = await ctx.author.voice.channel.connect()
                await self.append_music(ctx, link, applicant, voice_client)
                
            else:
                await smart_send(ctx, "먼저 음성 채널에 들어가 주세요")

        except Exception as err:
            print(err)
            await smart_send(ctx, "오류가 발생하여 음악을 재생할 수 없습니다.")

    @commands.hybrid_command(name="play", description = "유튜브 링크를 가져오면 음악을 재생한다")
    @wasu_think
    async def play(self, ctx, search: str):
        """유튜브 링크를 가져오면 음악을 재생한다."""
        try:
            # 음성 채널에 연결
            if ctx.author.voice: #사용자가 음성채널에 들어가 있는지. 들어가 있으면 True
                voice_client = ctx.guild.voice_client
                applicant = ctx.author.name #신청자 정보

                if not voice_client: #봇이 연결이 안되어 있을 경우, 연결시키기
                    voice_client = await ctx.author.voice.channel.connect() 
                
                #url이면 그대로, url이 아니라 검색어이면, url을 가져온다. 
                if search[:31] != "https://www.youtube.com/watch?v=":
                    search = youtube_api.get_video_link(search)
                    if search == "error message":
                        await smart_send(ctx, "해당하는 노래를 찾지 못 했습니다.")
                        return

                await self.append_music(ctx, search, applicant, voice_client)
                
            else:
                await smart_send(ctx, "먼저 음성 채널에 들어가 주세요")

        except Exception as err:
            print(err)
            await smart_send(ctx, "오류가 발생하여 음악을 재생할 수 없습니다.")

    @commands.hybrid_command(name = "que", description = "현재 대기열이 몇 개의 음악이 남았는지 알려준다")
    @wasu_think
    async def left_que(self, ctx):
        """현재 대기열이 몇 개의 음악이 남았는지 알려준다."""
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id 
        deq = get_server_data(guild_id)

        if len(deq) == 0: #큐가 비었을 경우. 
            await smart_send(ctx, "음악큐가 비어있습니다.")
            return
        message_temp = f'대기열에 총 {len(deq)}개의 곡이 존재합니다. \n'
        for i in range(min(20, len(deq))):
            message_temp += f'대기열 {i+1}번 - 추가자({deq[i][2]}): {deq[i][1]} \n'

        await smart_send(ctx, message_temp)

    @commands.hybrid_command(name = "skip", description = "현재 재생 중인 음악을 스킵한다.")
    @wasu_think
    async def skip(self, ctx):
        """현재 재생 중인 음악을 스킵한다."""
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await self.play_next(ctx)
            await smart_send(ctx, "다음 노래가 재생됩니다.")
        else:
            await smart_send(ctx, "현재 재생 중이 아니거나, 통화방에 없습니다.")

    @commands.hybrid_command(name = "pause", description = "현재 재생 중인 음악을 정지하거나 재개한다.")
    @wasu_think
    async def pause(self, ctx):
        """현재 재생 중인 음악을 정지하거나 재개한다."""
        voice_client = ctx.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
            await smart_send(ctx, "정지하였습니다.")
        else:
            voice_client.resume()
            await smart_send(ctx, "다시 시작하였습니다.")

    async def top10(self, ctx, top10_data, title, message_temp, title_data_position):
        #20초 제한시간
        view = View(timeout = 20) 

        for i in range(len(top10_data)):
            button = Button(label = f'{i+1}번 재생', style = discord.ButtonStyle.green)

            async def button_callback(interaction, button_index = i+1):
                await interaction.response.send_message(f'{button_index}번 노래가 추가 되었습니다.')
                link = youtube_api.get_video_link(top10_data[button_index-1][title_data_position])
                await self.play_only(ctx, link)

            async def time_out():
                for item in view.children:
                    item.disabled = True
                await message.edit(view = view)
            
            view.on_timeout = time_out    
            button.callback = button_callback
            view.add_item(button)

        message = await ctx.send(embed = discord.Embed(title = title, description = message_temp), view = view)

    @commands.hybrid_command(name = "search-server-top10", description = "해당 서버에서 가장 많이 재생된 음악을을 알려준다.")
    @wasu_think
    async def rank(self, ctx):
        """해당 서버에서 가장 많이 재생된 음악을을 알려준다."""
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id
        top10_data = to_mysql.rank(guild_id)

        message_temp = ''
        j = 1
        for i in top10_data:
            message_temp += f'{j} 위 {i[2]} : ```diff\n+{i[3]}회 재생 됨```\n'
            j += 1

        await self.top10(ctx, top10_data, "서버 재생 순위", message_temp, 2)

    @commands.hybrid_command(name = "search-user-top10", description = "해당 유저의 많이 들은 노래의 순위를 알려준다.")
    @wasu_think
    async def find_user(self, ctx, user_name : str = None):
        """해당 유저의 많이 들은 노래의 순위를 알려준다."""
        guild_id = ctx.guild.id

        if user_name == None:
            user_name = ctx.author.name
        top10_data = to_mysql.find_user(guild_id, user_name)
        
        message_temp = ''
        j = 1
        for i in top10_data:
            message_temp += f'{j} 위 {i[3]} : ```diff\n+{i[4]}회 재생 됨```\n'
            j += 1
        
        #없는 or 아직 아무것도 노래를 안 튼 경우
        if message_temp == '':
            await smart_send(ctx, "해당 서버에 없는 유저거나, 아직 아무노래도 틀지 않은 유저입니다.")
            return
        
        await self.top10(ctx, top10_data, f'{user_name}님의 재생 순위', message_temp, 3)

    @commands.hybrid_command(name = "how-many-played", description = "노래 제목을 입력하면, 그 노래가 해당서버에서 재생된 횟수를 알려준다.")
    @wasu_think
    async def how_many_played(self, ctx, title:str):
        """노래 제목을 입력하면, 그 노래가 해당서버에서 재생된 횟수를 알려준다."""        
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id 

        #대충 검색해도 그거와 관련된 것으로 대체해줌
        real_title = youtube_api.get_video_title(title) 
        played_number_data = to_mysql.find_music(guild_id, real_title) 

        if played_number_data != ():
            view = View(timeout = 20)

            button = Button(label = '재생', style = discord.ButtonStyle.green) 
            async def button_callback(interaction):
                await interaction.response.send_message('노래가 추가 되었습니다')
                link = youtube_api.get_video_link(real_title)
                await self.play_only(ctx, link)

            async def time_out():
                for item in view.children:
                    item.disabled = True
                await message.edit(view = view)

            view.on_timeout = time_out    
            button.callback = button_callback
            view.add_item(button)
            message = await ctx.send(embed = discord.Embed(title = f'{real_title} 재생 횟수', description = f'```diff\n+{played_number_data[0][3]}회 재생됨```'), view = view)
        else:
            await smart_send(ctx, "재생되지 않은 음악입니다.")

    @commands.hybrid_command(name = "is_play", description = "재생 중인지 알려준다")
    @wasu_think
    async def find(self, ctx):
        voice_client = ctx.guild.voice_client
        guild_id = ctx.guild.id 
        deq = get_server_data(guild_id)

        if voice_client.is_playing():
            await smart_send(ctx, "재생 중")
        else:
            await smart_send(ctx, "재생 중 아님")
            print(deq)

    @commands.hybrid_command(name = "playlist", description = "해당 유저가 많이 틀었던 노래 플레이리스트를 재생해준다.")
    @wasu_think
    async def playlist(self, ctx, user_name : str):
        pass

    
async def setup(bot):
    await bot.add_cog(youtube(bot))
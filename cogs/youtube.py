from discord.ext import commands
from collections import deque
import discord
import asyncio
import yt_dlp
import heapq
import functools
import sys, os

#최상위 디렉토리로 올라가기
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import to_mysql

#서버별 독립적인 데이터를 저장할 딕셔너리
server_queues = {}
server_played_number = {}
server_users = {}

def get_server_data(guild_id):
    if guild_id not in server_queues:
        server_queues[guild_id] = deque()
    if guild_id not in server_played_number:
        server_played_number[guild_id] = {}
    if guild_id not in server_users:
        server_users[guild_id] = {}
    return server_queues[guild_id], server_played_number[guild_id], server_users[guild_id]

def print_top3(content):
    top_3 = heapq.nlargest(3, content.items(), key = lambda x : x[1])
    message_temp = ''
    for i in range(len(top_3)):
        message_temp += f'{i+1} 위 {top_3[i][0]} : {top_3[i][1]} 회 재생 됨 \n'
    return message_temp

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
        deq, played_number, user = get_server_data(guild_id)

        if len(deq) > 0:
            next_play = deq.popleft()
            ctx.guild.voice_client.play(next_play[0], after= lambda e: asyncio.run_coroutine_threadsafe(
                self.handle_after_callback(ctx, e), ctx.bot.loop
            ))

            #sql 넣기
            print(guild_id, next_play[2], next_play[1])
            to_mysql.update_sql(guild_id, next_play[2], next_play[1])

            #그 음악이 틀어진 횟수를 넣기. 재생이 된 노래만 카운트. 대기열에 올라간 노래는 아직 카운트 x
            if next_play[1] in played_number:
                played_number[next_play[1]] += 1
            else:
                played_number[next_play[1]] = 1

            if next_play[2] in user: #신청인이 유저리스트에 있는 경우
                if next_play[1] in user[next_play[2]]:
                    user[next_play[2]][next_play[1]] += 1
                else:
                    user[next_play[2]][next_play[1]] = 1
            else:
                user[next_play[2]] = {next_play[1] : 1} #새로 만드는 경우, 신청인 이름 : {곡제목 : 재생횟수}

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
        deq, _, _ = get_server_data(guild_id)

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
        deq, _, _ = get_server_data(guild_id)
        
        if voice_client.is_playing():
            await smart_send(ctx, f'{is_playlist}곡이 대기열 {len(deq)}번부터 추가 되었습니다.')
        else:
            await smart_send(ctx, f'{is_playlist}곡이 대기열 0번부터 추가 되었습니다.')

        # 음악 재생
        if not voice_client.is_playing():
            await self.play_next(ctx)


    @commands.hybrid_command(name="play", description = "유튜브 링크를 가져오면 음악을 재생한다")
    @wasu_think
    async def play(self, ctx, url: str):
        """유튜브 링크를 가져오면 음악을 재생한다."""
        try:
            # 음성 채널에 연결
            if ctx.author.voice: #사용자가 음성채널에 들어가 있는지. 들어가 있으면 True
                voice_client = ctx.guild.voice_client
                applicant = ctx.author.name #신청자 정보

                if not voice_client: #봇이 연결이 안되어 있을 경우, 연결시키기
                    voice_client = await ctx.author.voice.channel.connect() 

                await self.append_music(ctx, url, applicant, voice_client)
                
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
        deq, _, _ = get_server_data(guild_id)

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
            smart_send(ctx, "정지하였습니다.")
        else:
            voice_client.resume()
            smart_send(ctx, "다시 시작하였습니다.")

    @commands.hybrid_command(name = "rank", description = "해당 서버에서 가장 많이 재생된 음악 top3를 알려준다.")
    @wasu_think
    async def rank(self, ctx):
        """해당 서버에서 가장 많이 재생된 음악 top3를 알려준다."""
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id 
        _, played_number, _ = get_server_data(guild_id)

        message_temp = print_top3(played_number)
        await smart_send(ctx, message_temp)

    @commands.hybrid_command(name = "count", description = "노래 제목(유튜브 제목이랑 완전히 같을 것)을 입력하면, 그 노래가 해당서버에서 재생된 횟수를 알려준다.")
    @wasu_think
    async def count(self, ctx, title:str):
        """노래 제목(유튜브 제목이랑 완전히 같을 것)을 입력하면, 그 노래가 해당서버에서 재생된 횟수를 알려준다."""        
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id 
        _, played_number, _ = get_server_data(guild_id)

        if title in played_number:
            await smart_send(ctx, f'{played_number[title]} 회 재생 됨')
        else:
            await smart_send(ctx, "재생되지 않은 음악입니다.")

    @commands.hybrid_command(name = "find", description = "find 뒤에 유저명을 입력하면, 그 유저의 top3 정보를 알려준다.!")
    @wasu_think
    async def find(self, ctx):
        """find 뒤에 유저명을 입력하면, 그 유저의 top3 정보를 알려준다."""
        guild_id = ctx.guild.id

        applicant = ctx.author.name
        _, _, user = get_server_data(guild_id)

        if applicant in user:
            message_temp = print_top3(user[applicant])
            await smart_send(ctx, message_temp) 
        else:
            await smart_send(ctx, "현재까지 재생하지 않았거나, 서버에 없습니다.")

    @commands.hybrid_command(name = "is_play", description = "재생 중인지 알려줌")
    @wasu_think
    async def find(self, ctx):
        voice_client = ctx.guild.voice_client
        guild_id = ctx.guild.id 
        deq, _, _ = get_server_data(guild_id)

        if voice_client.is_playing():
            await smart_send(ctx, "재생 중")
        else:
            await smart_send(ctx, "재생 중 아님")
            print(deq)

async def setup(bot):
    await bot.add_cog(youtube(bot))
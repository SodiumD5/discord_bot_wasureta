from discord.ext import commands
from collections import deque
import discord
import asyncio
import yt_dlp
import heapq

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

class youtube(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    yt_dl_opts = {'format': 'bestaudio[ext=webm]'}
    ytdl = yt_dlp.YoutubeDL(yt_dl_opts)
    ffmpeg_options = {'options' : '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}

    #음악 채워주는 함수
    def play_next(self, ctx):
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id 
        deq, played_number, user = get_server_data(guild_id)

        if len(deq) > 0:
            next_play = deq.popleft()
            ctx.guild.voice_client.play(next_play[0], after = lambda e : (print(f'Error {e}') if e else self.play_next(ctx)))

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

    @commands.command(name="play")
    async def play(self, ctx, url: str):
        """유튜브 링크를 가져오면 음악을 재생한다."""
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id 
        deq, _, _ = get_server_data(guild_id)

        try:
            # 음성 채널에 연결
            if ctx.author.voice: #사용자가 음성채널에 들어가 있는지. 들어가 있으면 True
                voice_client = ctx.guild.voice_client
                if not voice_client: #봇이 연결이 안되어 있을 경우, 연결시키기
                    voice_client = await ctx.author.voice.channel.connect() 

                # YouTube에서 오디오 스트림 가져오기
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(url, download=False)) #url 정보를 뽑아서 저장하는 딕셔너리임

                song = data['url']
                title = data['title']
                player = discord.FFmpegPCMAudio(song, executable="C:/ffmpeg/bin/ffmpeg.exe", **self.ffmpeg_options)
                applicant = ctx.author.name

                deq.append([player, title, applicant]) #곡의 정보, 제목, 그 곡의 신청자이름
                if voice_client.is_playing():
                    await ctx.channel.send(f'대기열 {len(deq)}번 입니다.', reference = ctx.message)
                else:
                    await ctx.channel.send(f'대기열 0번 입니다.', reference = ctx.message)

                # 음악 재생
                if not voice_client.is_playing():
                    self.play_next(ctx)

            else:
                await ctx.send("먼저 음성 채널에 들어가 주세요")

        except Exception as err:
            print(err)
            await ctx.send("오류가 발생하여 음악을 재생할 수 없습니다.")

    @commands.command(name = "que")
    async def left_que(self, ctx):
        """현재 대기열이 몇 개의 음악이 남았는지 알려준다."""
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id 
        deq, _, _ = get_server_data(guild_id)

        if len(deq) == 0: #큐가 비었을 경우. 
            await ctx.channel.send("음악큐가 비어있습니다.")
            return
        message_temp = ''
        for i in range(len(deq)):
            message_temp += f'대기열 {i+1}번 - 추가자({deq[i][2]}): {deq[i][1]} \n'
        await ctx.channel.send(message_temp, reference = ctx.message)

    @commands.command(name = "skip")
    async def skip(self, ctx):
        """현재 재생 중인 음악을 스킵한다."""
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            self.play_next(ctx)
        else:
            await ctx.send("현재 재생 중이 아니거나, 통화방에 없습니다.")

    @commands.command(name = "pause")
    async def pause(self, ctx):
        """현재 재생 중인 음악을 정지하거나 재개한다."""
        voice_client = ctx.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
        else:
            voice_client.resume()

    @commands.command(name = "rank")
    async def rank(self, ctx):
        """해당 서버에서 가장 많이 재생된 음악 top3를 알려준다."""
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id 
        _, played_number, _ = get_server_data(guild_id)

        message_temp = print_top3(played_number)
        await ctx.channel.send(message_temp)

    @commands.command(name = "count")
    async def count(self, ctx, title:str):
        """노래 제목(유튜브 제목이랑 완전히 같을 것)을 입력하면, 그 노래가 해당서버에서 재생된 횟수를 알려준다."""
        #해당 길드에서의 큐랑 재생 횟수를 가져옴. 
        guild_id = ctx.guild.id 
        _, played_number, _ = get_server_data(guild_id)

        if title in played_number:
            await ctx.send(f'{played_number[title]} 회 재생 됨')
        else:
            await ctx.send("재생되지 않은 음악입니다.")

    @commands.command(name = "find")
    async def find(self, ctx):
        """find 뒤에 유저명을 입력하면, 그 유저의 top3 정보를 알려준다."""
        guild_id = ctx.guild.id

        applicant = ctx.author.name
        _, _, user = get_server_data(guild_id)

        if applicant in user:
            message_temp = print_top3(user[applicant])
            await ctx.send(message_temp) 
        else:
            await ctx.send("현재까지 재생하지 않았거나, 서버에 없습니다.")
async def setup(bot):
    await bot.add_cog(youtube(bot))
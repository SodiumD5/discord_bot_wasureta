from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands
from collections import deque
import discord
import asyncio
import yt_dlp
import functools
import sys, os

#최상위 디렉토리로 올라가기
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import to_mysql, crolling

#서버별 독립적인 데이터를 저장할 딕셔너리 (절대 전역 변수 안됨)
server_queues = {}
server_nowplay = {}
server_isrepeat = {}

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
        deq = get_server_data(guild_id)

        if guild_id not in server_isrepeat:
            server_isrepeat[guild_id] = "반복 안 함"
        if server_isrepeat[guild_id] == "이 곡 반복" or server_isrepeat[guild_id] == "전체 반복":
            url = to_mysql.find_url_data(server_nowplay[guild_id][1])
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self.sodiumd_extract_info, url[0][2])
            new_url = data['url']
            new_music_info = discord.FFmpegPCMAudio(new_url, executable="C:/ffmpeg/bin/ffmpeg.exe", **self.ffmpeg_options)

            if server_isrepeat[guild_id] == "이 곡 반복":
                deq.appendleft([new_music_info, server_nowplay[guild_id][1], server_nowplay[guild_id][2]])
            elif server_isrepeat[guild_id] == "전체 반복": 
                deq.append([new_music_info, server_nowplay[guild_id][1], server_nowplay[guild_id][2]]) #deq꺼를 그대로 가져와서 0번이 변환된 url, 1번이 title, 2번이 신청자이름임 

        if len(deq) > 0:
            server_nowplay[guild_id] = deq[0]
            next_play = deq.popleft()
            ctx.guild.voice_client.play(next_play[0], after= lambda e: asyncio.run_coroutine_threadsafe(
                self.handle_after_callback(ctx, e), ctx.bot.loop
            ))

            #sql 넣기
            to_mysql.add_sql(guild_id, next_play[2], next_play[1])
        else: #큐가 다 끝남 -> 리소스 줄이기 위해서 나가기
            await ctx.guild.voice_client.disconnect()
            await smart_send(ctx, "연결을 끊었습니다.")


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

    async def append_music(self, ctx, title, url, applicant, voice_client, *is_wasu):
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
            new_url = data['url']
            music_info = discord.FFmpegPCMAudio(new_url, executable="C:/ffmpeg/bin/ffmpeg.exe", **self.ffmpeg_options)
            if not is_wasu:
                deq.append([music_info, title, applicant]) #곡의 정보, 제목, 그 곡의 신청자이름
                await self.call_executer(ctx, voice_client, is_playlist, title)
            else:
                deq.append([music_info, title, applicant])
                await self.call_executer(ctx, voice_client, is_playlist, "Wasureta 원곡")


    async def call_executer(self, ctx, voice_client, is_playlist, *args):
        guild_id = ctx.guild.id 
        deq = get_server_data(guild_id)
        
        #곡이 와수레타일 때때
        if args[0] == "Wasureta 원곡":
            await smart_send(ctx, 'Wasureta가 다음곡으로 선정되었습니다.')
        else:
            if voice_client.is_playing():
                if is_playlist == 1:
                    await smart_send(ctx, f'{args[0]} \n대기열 {len(deq)}번에 추가 되었습니다.')
                else:
                    await smart_send(ctx, f'{is_playlist}곡이 대기열 {len(deq)}번부터 {len(deq)+is_playlist-1}번까지 추가 되었습니다.')
            else:
                if is_playlist == 1:
                    await smart_send(ctx, f'노래 제목 : {args[0]} \n대기열 0번에 추가 되었습니다.')
                else:
                    await smart_send(ctx, f'{is_playlist}곡이 대기열 0번부터 {len(deq)+is_playlist-1}번까지 추가 되었습니다.')

        # 음악 재생
        if not voice_client.is_playing():
            await self.play_next(ctx)

    async def play_only(self, ctx, title, link, *is_wasu):
        try:
            # 음성 채널에 연결
            if ctx.author.voice: #사용자가 음성채널에 들어가 있는지. 들어가 있으면 True
                voice_client = ctx.guild.voice_client
                applicant = ctx.author.name #신청자 정보

                if not voice_client: #봇이 연결이 안되어 있을 경우, 연결시키기
                    voice_client = await ctx.author.voice.channel.connect()
                if is_wasu:
                    await self.append_music(ctx, title, link, applicant, voice_client, True)
                else:
                    await self.append_music(ctx, title, link, applicant, voice_client)
                
            else:
                await smart_send(ctx, "먼저 음성 채널에 들어가 주세요")

        except Exception as err:
            print(err)
            await smart_send(ctx, "오류가 발생하여 음악을 재생할 수 없습니다.")

    @commands.hybrid_command(name="play", description = "유튜브 링크를 가져오면 음악을 재생한다/검색어를 입력하면 5개 중에 선택이 가능하다.")
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
                    server_isrepeat[ctx.guild.id] = "반복 안 함"
                
                #url이면 그대로, url이 아니라 검색어이면, url을 가져온다. -> 5개를 가져와서 선택할 수 있도록
                if search[:24] != "https://www.youtube.com/":
                    view = View(timeout = 20)

                    message_temp = ''
                    search_output = crolling.search_link(search, 5)

                    for i in range(len(search_output)):
                        message_temp += f'{i+1}번 검색결과 : {search_output[i][0]} \n\n'

                    for i in range(len(search_output)):
                        button = Button(label = f'{i+1}번 재생', style = discord.ButtonStyle.green)

                        async def button_callback(interaction, button_index = i+1):
                            await interaction.response.send_message(f'{button_index}번 노래가 추가 되었습니다.')
                            link = search_output[button_index-1][1]
                            title = search_output[button_index-1][0]
                            await self.append_music(ctx, title, link, applicant, voice_client)
                            
                            to_mysql.save_title_data(title, link)
                            #한 번만 클릭되게
                            for item in view.children:
                                item.disabled = True
                            await message.edit(view = view)

                        button.callback = button_callback
                        view.add_item(button)

                    async def time_out():
                        for item in view.children:
                            item.disabled = True
                        await message.edit(view = view)

                    view.on_timeout = time_out
                    message = await ctx.send(embed = discord.Embed(title = f"{search} 검색결과", description = message_temp), view = view)

                    if search_output == "error message":
                        await smart_send(ctx, "해당하는 노래를 찾지 못 했습니다.")
                        return
                    
                else: #url을 입력 받았을 경우에 db에 저장
                    title = crolling.search_title(search)
                    to_mysql.save_title_data(title, search)

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
        deq= get_server_data(guild_id)

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
            voice_client.pause()
            await self.play_next(ctx)
            if voice_client and voice_client.is_playing():
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
    
    async def top10(self, ctx, top10_data, title, message_temp, title_data_position, *user_name): #랜덤플리를 쓸 때 필요한 args
        #20초 제한시간
        view = View(timeout = 20) 

        for i in range(len(top10_data)):
            button = Button(label = f'{i+1}번 재생', style = discord.ButtonStyle.green)

            async def button_callback(interaction, button_index = i+1):
                await interaction.response.send_message(f'{button_index}번 노래가 추가 되었습니다.')
                title = top10_data[button_index-1][title_data_position]
                link = to_mysql.find_url_data(title) # -> 이건 db에서 가져오자 1건만 가져옴. 
                await self.play_only(ctx, title, link[0][2])

            button.callback = button_callback
            view.add_item(button)

        if user_name:
            guild_id = ctx.guild.id 
            deq= get_server_data(guild_id)
            applicant = ctx.author.name

            playall = Button(label = "모두 재생", style = discord.ButtonStyle.primary)

            async def playall_callback(interaction):
                # voice_client = ctx.guild.voice_client
                await interaction.response.send_message(f"{len(top10_data)}곡이 대기열 {len(deq)}번 부터 추가 되었습니다.")
                title = top10_data[0][title_data_position]
                link = to_mysql.find_url_data(title)[0][2] # -> 이거도 db에서 가져오는거로 (1곡만)

                #첫 곡 던지고
                await self.play_only(ctx, title, link)
                
                #나머지곡들 -> 남은 9곡은 이미 출력을 했기 때문에, 비동기로 하면 순서가 꼬이므로, 동기처리한다. 
                for i in range(1, len(top10_data)):
                    link = to_mysql.find_url_data(top10_data[i][title_data_position]) # -> 이거도 db에서 가져오는거로 (1곡씩만)
                    
                    loop = asyncio.get_event_loop()
                    video_data = await loop.run_in_executor(None, self.sodiumd_extract_info, link[0][2])

                    title = top10_data[i][title_data_position]
                    music_info = discord.FFmpegPCMAudio(video_data['url'], executable="C:/ffmpeg/bin/ffmpeg.exe", **self.ffmpeg_options)
                    deq.append([music_info, title, applicant])

                for item in view.children:
                    item.disabled = True
                await message.edit(view = view)

            playall.callback = playall_callback
            view.add_item(playall)

        async def time_out():
            for item in view.children:
                item.disabled = True
            await message.edit(view = view)
        view.on_timeout = time_out  
        
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
            message_temp += f'{j}위 {i[2]} : ```diff\n+{i[3]}회 재생 됨```\n'
            j += 1

        await self.top10(ctx, top10_data, f"{ctx.guild.name}서버 재생 순위", message_temp, 2)

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
            message_temp += f'{j}위 {i[3]} : ```diff\n+{i[4]}회 재생 됨```\n'
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
        result = crolling.search_link(title, 1) # -> 1곡씩만 크롤링으로 가져오기
        real_title = result[0][0]
        played_number_data = to_mysql.find_music(guild_id, real_title) 

        if played_number_data != ():
            view = View(timeout = 20)

            button = Button(label = '재생', style = discord.ButtonStyle.green) 
            async def button_callback(interaction):
                await interaction.response.send_message('노래가 추가 되었습니다')
                link = result[1] # -> 위에서 가져온거 돌려쓰면 될 듯?
                await self.play_only(ctx, real_title, link)

            async def time_out():
                for item in view.children:
                    item.disabled = True
                await message.edit(view = view)

            view.on_timeout = time_out    
            button.callback = button_callback
            view.add_item(button)
            message = await ctx.send(embed = discord.Embed(title = f'{real_title} 재생 횟수', description = f'```diff\n+{played_number_data[0][3]}회 재생됨```'), view = view)
        else:
            view = View()
            await ctx.send(embed = discord.Embed(title = f'{real_title} 재생 횟수', description = f'```diff\n-재생되지 않은 음악입니다.```'), view = view)

    @commands.hybrid_command(name = "leave", description = "wasureta를 내보낸다")
    @wasu_think
    async def leave(self, ctx):
        """wasureta를를 내보낸다."""
        voice_client = ctx.guild.voice_client

        if ctx.author.voice and ctx.guild.voice_client and voice_client.is_playing():
            await ctx.guild.voice_client.disconnect()
            await smart_send(ctx, "연결을 끊었습니다.")
        else:
            await smart_send(ctx, "이미 연결이 끊어져있습니다.")

    @commands.hybrid_command(name = "wasu", description = "wasureta를 바로 다음 곡으로 선정한다.")
    @wasu_think
    async def wasu(self, ctx):
        """wasureta를 바로 다음 곡으로 선정한다."""
        await self.play_only(ctx, "wasureta","https://www.youtube.com/watch?v=NaBF7qsPxWg", True)

    @commands.hybrid_command(name = "now-playing", description = "현재 재생 중인 노래의 제목과 링크를 준다.")
    @wasu_think
    async def wasu(self, ctx):
        """현재 재생 중인 노래의 제목과 링크를 준다."""
        voice_client = ctx.guild.voice_client
        guild_id = ctx.guild.id

        if ctx.guild.voice_client and voice_client.is_playing():
            now_link = to_mysql.find_url_data(server_nowplay[guild_id][1]) #db에서 가져오면 됨
            await smart_send(ctx, f'현재 곡 : {server_nowplay[guild_id][1]} \n링크 : {now_link[0][2]}')
        else:
            await smart_send(ctx, "현재 재생 중이 아닙니다.")

    @commands.hybrid_command(name = "playlist", description = "해당 유저가 많이 틀었던 노래 플레이리스트를 랜덤으로 뽑아준다.")
    @app_commands.describe(
        user_name = "누구의 플리를 찾을 지 입력(비워두면 서버 전체에서 검색한다)",
        start_num = "몇 위부터 검색할 지 입력(비워두면 1위부터 검색한다)",
        end_num = "몇 위까지 검색할 지 입력(비워두면 50위까지 검색한다)"
    )
    @wasu_think
    async def playlist(self, ctx, user_name : str = None, start_num : int = None, end_num : int = None):
        """해당 유저가 많이 틀었던 노래 플레이리스트를 랜덤으로 뽑아준다."""
        #기본값 설정
        guild_id = ctx.guild.id
        if start_num == None:
            start_num = 1
        if end_num == None:
            end_num = start_num+50

        result = to_mysql.random_user_playlist(guild_id, user_name, start_num, end_num)
        message_temp = ''
        j = 1

        #입력값처리
        if start_num < 1 or end_num < 1:
            smart_send(ctx, "잘못된 입력값입니다.")
            return
        if start_num > end_num:
            temp = end_num
            end_num = start_num
            start_num = temp
        
        #비워진 경우 서버이다.
        if user_name == None:
            for i in result:
                message_temp += f'{j}번 노래 : {i[2]} \n\n'
                j += 1

            user_name = ctx.guild.name
            if message_temp == '':
                await smart_send(ctx, "노래가 검색되지 않았습니다.")
            else:
                await self.top10(ctx, result, f"{user_name}서버 랜덤 노래", message_temp, 2, user_name)
        else:
            for i in result:
                message_temp += f'{j}번 노래 : {i[3]} \n\n'
                j += 1

            if message_temp == '':
                await smart_send(ctx, "없는 유저이거나, 해당하는 순위범위에 노래가 없습니다.")
            else:
                await self.top10(ctx, result, f"{user_name}의 랜덤 노래", message_temp, 3, user_name)        

    @commands.hybrid_command(name = "repeat", description = "한 곡 반복이나, 현재플리를 반복 할 수 있습니다.")
    @wasu_think
    async def repeat(self, ctx):
        """한 곡 반복이나, 현재플리를 반복 할 수 있습니다."""
        guild_id = ctx.guild.id
        voice_client = ctx.guild.voice_client
        if not (ctx.author.voice and ctx.guild.voice_client and voice_client.is_playing()):
            await smart_send(ctx, "먼저 재생을 시작하세요.")

        view = View(timeout=20)
        not_song_repeat = Button(label = "반복 안 함", style = discord.ButtonStyle.red)
        one_song_repeat = Button(label = "이 곡 반복", style = discord.ButtonStyle.green)
        all_song_repeat = Button(label = "전체 반복", style = discord.ButtonStyle.primary)

        async def not_song_callback(interaction):
            server_isrepeat[guild_id] = "반복 안 함"
            await interaction.response.edit_message(
                embed = discord.Embed(title = f'{ctx.guild.name} 서버 반복 설정', description = f'현재 상태 : {server_isrepeat[guild_id]}'), view = view)
            
            for item in view.children:
                item.disabled = True
            await message.edit(view = view)
            
        async def one_song_callback(interaction):
            server_isrepeat[guild_id] = "이 곡 반복"
            await interaction.response.edit_message(
                embed = discord.Embed(title = f'{ctx.guild.name} 서버 반복 설정', description = f'현재 상태 : {server_isrepeat[guild_id]}'), view = view)
            
            for item in view.children:
                item.disabled = True
            await message.edit(view = view)

        async def all_song_callback(interaction):
            server_isrepeat[guild_id] = "전체 반복"
            await interaction.response.edit_message(
                embed = discord.Embed(title = f'{ctx.guild.name} 서버 반복 설정', description = f'현재 상태 : {server_isrepeat[guild_id]}'), view = view)
            
            for item in view.children:
                item.disabled = True
            await message.edit(view = view)
        
        not_song_repeat.callback = not_song_callback
        one_song_repeat.callback = one_song_callback
        all_song_repeat.callback = all_song_callback

        async def time_out():
            for item in view.children:
                item.disabled = True
            await message.edit(view = view)
        view.on_timeout = time_out
        
        if server_isrepeat[guild_id] == "반복 안 함":
            view.add_item(one_song_repeat)
            view.add_item(all_song_repeat)
        elif server_isrepeat[guild_id] == "이 곡 반복":
            view.add_item(not_song_repeat)
            view.add_item(all_song_repeat)
        else: #전체 반복 
            view.add_item(not_song_repeat)
            view.add_item(one_song_repeat)
        
        message = await ctx.send(embed = discord.Embed(title = f'{ctx.guild.name} 서버 반복 설정', description = f'현재 상태 : {server_isrepeat[guild_id]}'), view = view)

async def setup(bot):
    await bot.add_cog(youtube(bot))
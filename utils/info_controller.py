import random
from data.guild import Song
from data.user import User
from utils.forms import Form
from utils.music_controller import music_controller
from database.database_search import database_search
from utils.error_controller import error_handler, report


class InfoController:
    def __init__(self):
        pass
    
    @error_handler(caller_name="last-played")
    async def take_last_played(self, ctx):
        player = music_controller.get_player(guild=ctx.guild, voice_client=ctx.voice_client)

        try:
            result = database_search.get_last_played_song(server_id=player.guild.id)
            if not result:
                form = Form("서버에서 노래를 재생한 기록이 없습니다.")
                await form.smart_send(ctx)
                return

            youtube_url, played_at, user_name, display_name = result["youtube_url"], result["played_at"], result["user_name"], result["display_name"]
            result["url"] = None  # Song객체를 재활용하려면 어쩔 수 없음...

            applicant = User(name=user_name, display_name=display_name)
            last_song = player.guild.last_played = Song(applicant=applicant, youtube_url=youtube_url, video_info=result)
            last_song.start_time = played_at

            message = last_song.song_info(caller="last-played")
            form = Form(message=message, title=f"마지막 재생 곡", guild=player.guild, player=player)
            await form.show_last_played(ctx)
        except:
            report.error_record(caller="take_last_played", error=e)

    @error_handler(caller_name="ranking")
    async def take_ranking(self, ctx, order_by):
        if order_by == "신청곡 수 순위":
            results = database_search.get_top_users(server_id=ctx.guild.id)

            title = f"{ctx.guild.name} 서버 신청곡 수 순위"
            message = ""
            for idx, result in enumerate(results):
                message += f"**{idx+1}위. {result['display_name']} : {result['play_count']}번 재생됨**\n\n"
            form = Form(message=message, title=title)
            await form.basic_view(ctx)
        elif order_by == "청취 시간 순위":
            form = Form(message="아몰랑~", title="아직 안 만듬")
            await form.basic_view(ctx)

    def _format_song_message(self, results, ranking_count=True):
        message = ""
        for idx, result in enumerate(results):
            if ranking_count:
                message += f"**{idx+1}위.** {result['title']}\n**{result['play_count']}번 재생됨**\n\n"
            else:
                message += f"**{idx+1}.** {result['title']}\n\n"
        return message

    def _get_empty_message(self, member_name, guild_name):
        if member_name is None:
            return f"{guild_name}서버의 재생 기록이 없습니다."
        else:
            return f"{member_name}님은 아직 노래를 재생하지 않았습니다."

    async def _send_song_list(self, ctx, member_name, title_suffix, ranking_count=True, limit=10, randomize=False):
        if member_name is None:
            results = database_search.get_top_songs(server_id=ctx.guild.id, limit=limit)
            title = f"{ctx.guild.name} 서버 {title_suffix}"
        else:
            results = database_search.get_top_songs_by_user(server_id=ctx.guild.id, display_name=member_name, limit=limit)
            title = f"{member_name}의 {title_suffix}"

        if not results:
            message = self._get_empty_message(member_name, ctx.guild.name)

        if randomize and results:
            sample_size = min(10, len(results))
            results = random.sample(results, sample_size)

        message = self._format_song_message(results, ranking_count)

        form = Form(message=message, title=title, data=results)
        await form.show_list_view(ctx=ctx, number_of_button=len(results) + 1)

    @error_handler(caller_name="search-top10")
    async def take_top_songs(self, ctx, member_name):
        await self._send_song_list(ctx=ctx, member_name=member_name, title_suffix="인기 노래 차트", ranking_count=True)

    @error_handler(caller_name="playlist")
    async def make_playlist(self, ctx, member_name, limit):
        await self._send_song_list(ctx=ctx, member_name=member_name, title_suffix="랜덤 플리", ranking_count=False, limit=limit, randomize=True)


info_controller = InfoController()

from data.guild import Song
from data.user import User
from utils.forms import Form
from utils.music_controller import music_controller
from database.database_search import database_search


class InfoController:
    def __init__(self):
        pass

    async def take_last_played(self, ctx):
        player = music_controller.get_player(guild=ctx.guild, voice_client=ctx.voice_client)

        try:
            result = database_search.get_last_played_song(server_id=player.guild.id)
            youtube_url, played_at, user_name, display_name = result["youtube_url"], result["played_at"], result["user_name"], result["display_name"]
            result["url"] = None  # Song객체를 재활용하려면 어쩔 수 없음...

            applicant = User(name=user_name, display_name=display_name)
            last_song = player.guild.last_played = Song(applicant=applicant, youtube_url=youtube_url, video_info=result)
            last_song.start_time = played_at

            message = last_song.song_info(caller="last-played")
            form = Form(message=message, title=f"마지막 재생 곡", guild=player.guild, player=player)
            await form.show_last_played(ctx)
        except TypeError as e:
            form = Form("서버에서 노래를 재생한 기록이 없습니다.")
            await form.smart_send(ctx)
            print(f"에러 : {e}")

    async def take_ranking(self, ctx, order_by):
        if order_by == "신청곡 수 순위":
            results = database_search.get_top_players(server_id=ctx.guild.id)
            title = f"{ctx.guild.name} 서버 신청곡 수 순위"
            message = ""
            for idx, result in enumerate(results):
                message += f"{idx+1}위. {result['display_name']} : `{result['play_count']}`\n\n"
            form = Form(message=message, title=title)
            await form.basic_view(ctx)
        elif order_by == "청취 시간 순위":
            form = Form(message="아몰랑~", title="아직 안 만듬")
            await form.basic_view(ctx)


info_controller = InfoController()

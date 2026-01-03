from utils.forms import Form
from utils.music_controller import music_controller


class InfoController:
    def __init__(self):
        pass

    async def take_last_played(self, ctx):
        player = music_controller.get_player(ctx.guild.id, ctx.voice_client)

        try:
            message = player.guild.last_played.song_info(caller="last-played")
            form = Form(message=message, title=f"마지막 재생 곡", guild=player.guild, player=player)
            await form.show_last_played(ctx)
        except AttributeError:
            form = Form("서버에서 노래를 재생한 기록이 없습니다.")
            await form.smart_send(ctx)
        except Exception as e:
            print(e)


info_controller = InfoController()

from utils.stopwatch import Stopwatch
import math


def time_to_korean(time):
    time = round(time)
    hour, minute, second = time // 3600, time // 60 - 60 * (time // 3600), time % 60

    if hour == minute == 0:
        return f"{second}초"
    elif hour == 0:
        return f"{minute}분 {second}초"
    else:
        return f"{hour}시간 {minute}분 {second}초"


class Song:
    def __init__(self, applicant, youtube_url, video_info, audio_source=None):
        # 스트림 정보
        self.youtube_url = youtube_url
        self.video_info = video_info
        self.stream_url = self.video_info["url"]
        self.audio_source = audio_source
        self.video_id = self.video_info["id"]

        # 노래 정보
        self.title = self.video_info["title"]
        self._set_thumnail_url()
        self.duration = self.video_info["duration"]
        self.stopwatch = Stopwatch()
        self.played_time = 0
        self.start_time = None

        # 신청자 정보
        self.applicant_name = applicant.name
        self.applicant_displayname = applicant.display_name

    def pause(self, pause_start=True):
        if pause_start:
            part_time = self.stopwatch.reset()
            self.played_time += part_time
        else:
            self.stopwatch.reset()

    def jump(self, target_time: int):
        self.stopwatch.reset()
        self.played_time = target_time

    def _set_thumnail_url(self):
        self.thumbnail_url = f"https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg"

    def song_info(self, caller="que"):
        part_time = self.stopwatch.reset()
        self.played_time += part_time

        progress = ""

        filled_box = math.floor(self.played_time * 20 / self.duration)
        for _ in range(filled_box):
            progress += "█"
        for _ in range(20 - filled_box):
            progress += "─"

        song_type = "현재" if caller == "que" else "마지막"
        message = f"{song_type} 곡 - 추가자({self.applicant_displayname}) : {self.title}\n링크 : {self.youtube_url}\n\n"
        if caller == "que":
            message += f"진행도 : {progress}\n **(재생시간 : {time_to_korean(self.played_time)} / {time_to_korean(self.duration)})**"
        else:
            message += f"(재생시간 : {time_to_korean(self.duration)})\n"
            message += f"마지막으로 재생한 시간 : {self.start_time}"
        return message

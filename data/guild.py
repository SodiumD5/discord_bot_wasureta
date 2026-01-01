import math
from collections import deque
from utils.stopwatch import Stopwatch


# discord.py에서는 서버를 guild라는 표현으로 쓴다. 모든 서버에 대한 의미는 guild라는 단어로 통일한다.
# 이 파일에서는 하나의 guild 내 에서의 정보만을 생각한다.
class Guild:
    def __init__(self):
        self.queue = deque()
        self.now_playing = None
        self.last_played = None
        self.repeat = "반복 안 함"

    def add_queue(self, data, pos=-1):
        if pos == 0:
            self.queue.appendleft(data)
        elif pos == -1:
            self.queue.append(data)

    def pop_queue(self, pos=0):
        if self.queue and pos == 0:
            song = self.queue.popleft()
            return song
        elif self.queue and pos == -1:
            song = self.queue.pop()
            return song
        elif self.queue:  # 큐에서 삭제용도
            del self.queue[pos]
        return None

    def is_queue_empty(self):
        return len(self.queue) == 0

    def get_queue_length(self):
        return len(self.queue)

    def get_queue_info(self, page, max_results):
        message = ""
        for idx in range(10 * page, 10 * page + max_results):
            searched_song = self.queue[idx]
            duration = searched_song.time_to_korean(searched_song.duration)
            message += f"{idx+1}번 (추가자 - {searched_song.applicant_displayname}) : {searched_song.title} \n**(재생시간 : {duration})**\n\n"

        return message


class Song:
    def __init__(self, youtube_url, video_info, audio_source, applicant):
        # 스트림 정보
        self.youtube_url = youtube_url
        self.video_info = video_info
        self.stream_url = self.video_info["url"]
        self.audio_source = audio_source

        # 노래 정보
        self.title = self.video_info["title"]
        self._set_thumnail_url()
        self.duration = self.video_info["duration"]
        self.stopwatch = Stopwatch()
        self.played_time = 0

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

    def time_to_korean(self, time):
        time = round(time)
        hour, minute, second = time // 3600, time // 60 - 60 * (time // 3600), time % 60

        if hour == minute == 0:
            return f"{second}초"
        elif hour == 0:
            return f"{minute}분 {second}초"
        else:
            return f"{hour}시간 {minute}분 {second}초"

    def _set_thumnail_url(self):
        video_id = self.video_info["id"]
        self.thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

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
            message +=  f"진행도 : {progress}\n **(재생시간 : {self.time_to_korean(self.played_time)} / {self.time_to_korean(self.duration)})**"
        else:
            message += f"(재생시간 : {self.time_to_korean(self.duration)})"
        return message

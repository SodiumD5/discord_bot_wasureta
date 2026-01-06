from collections import deque
from data.song import time_to_korean



# discord.py에서는 서버를 guild라는 표현으로 쓴다. 모든 서버에 대한 의미는 guild라는 단어로 통일한다.
# 이 파일에서는 하나의 guild 내 에서의 정보만을 생각한다.
class Guild:
    def __init__(self, guild):
        self.id = guild.id
        self.name = guild.name
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
            duration = time_to_korean(searched_song.duration)
            message += f"{idx+1}번 (추가자 - {searched_song.applicant_displayname}) : {searched_song.title} \n**(재생시간 : {duration})**\n\n"

        return message

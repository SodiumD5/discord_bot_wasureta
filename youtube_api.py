import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.tools import argparser

def base_setting(search):
    load_dotenv()
    YOUTUBE_KEY = os.getenv("YOUTUBE_API") # 발급 받은 API 키 삽입
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_KEY)

    search_response = youtube.search().list(q = search,  # 검색어
                                            order = "relevance", # 정확도순 
                                            part = "snippet",  # 필수매개변수(API 응답이 포함하는 search 리소스 속성 하나 이상의 쉼표로 구분된 목록을 지정)
                                            maxResults = 1).execute() # 결과 집합에 반환해야 하는 최대 항목 수를 지정 0~50
                                            # execute()로 수행
    return search_response

def get_video_link(search):
    search_response = base_setting(search)

    for item in search_response.get("items", []):
        if item["id"]["kind"] == "youtube#video":  # 동영상 결과 확인
            video_id = item["id"]["videoId"]      # 동영상 ID 추출
            video_link = f"https://www.youtube.com/watch?v={video_id}"
            return video_link
        else:
            return "error message"

def get_video_title(search):
    search_response = base_setting(search)

    for item in search_response.get("items", []):
        if item["id"]["kind"] == "youtube#video":  # 동영상 결과 확인
            video_title = item["title"]      # 동영상 ID 추출
            return video_title
        else:
            return "error message"
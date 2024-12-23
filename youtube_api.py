# import os
# from dotenv import load_dotenv
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# from oauth2client.tools import argparser
import crolling

# def base_setting(search):
#     # load_dotenv()
#     # YOUTUBE_KEY = os.getenv("YOUTUBE_API") # 발급 받은 API 키 삽입
#     # youtube = build('youtube', 'v3', developerKey=YOUTUBE_KEY)

#     search_response = crolling.search_return(search)
#     return search_response


def get_video_link_title(search, how_many_music):
    search_response = crolling.search_link(search, how_many_music)
    return search_response

















# def get_video_link(search):
#     search_response = crolling.search_return(search)
    


#     # search_response = base_setting(search)

#     # for item in search_response.get("items", []):
#     #     if item["id"]["kind"] == "youtube#video":  # 동영상 결과 확인
#     #         video_id = item["id"]["videoId"]      # 동영상 ID 추출
#     #         video_link = f"https://www.youtube.com/watch?v={video_id}"
#     #         return video_link
#     #     else:
#     #         return "error message"

# def get_video_title(search):


#     # search_response = base_setting(search)
#     # items = search_response.get("items", [])
#     # title = items[0].get('snippet', {}).get('title', '제목 없음')

#     # if title != None:
#     #     return title
#     # else:
#     #     return "error message"
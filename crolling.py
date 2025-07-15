from yt_dlp import YoutubeDL

def search_youtube(query, max_results):
    options = {
        'quiet': True,
        'extract_flat': True,  # 메타데이터만 가져오기
        'noplaylist': True,    # 재생목록 제외
    }

    with YoutubeDL(options) as ydl:
        results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        videos = results['entries']
        return [{"title": video["title"], "url": video["url"]} for video in videos]
    
# 실행
def search_link(keyward, max_results):
    results = search_youtube(keyward, max_results)

    search_results = []
    for video in results:
        search_results.append([video["title"], video["url"]])
    return search_results

def search_title(url):
    options = {
        'quiet': True,
    }

    with YoutubeDL(options) as ydl:
        # URL에서 메타데이터 추출
        info = ydl.extract_info(url, download=False)
        return info.get("title")

def search_swms_videos():
    pass
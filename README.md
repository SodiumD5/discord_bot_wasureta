# Wasureta 
discord bot 개발 중
음악 재생을 하는데, 각 서버마다 틀어진 노래의 순위를 저장해둔다. 

since 2024.11.01

슬래시 command !command 둘 다 가능. 

함수 호출 구조조
play -> append_music -> call_executer -> play_next
play -> append_music -> one_song_player 
                     -> left_song_player -> one_song_player


requirements
pip install Flask discord python-dotenv yt-dlp pymysql PrettyTable asyncio
ffmpeg를 다운 받아야한다. 
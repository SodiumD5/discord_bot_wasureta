import datetime
from typing import TYPE_CHECKING
from database.database_init import DatabaseInit

if TYPE_CHECKING:
    from data.guild import Guild


class DatabaseInsert(DatabaseInit):
    def __init__(self):
        super().__init__()

    def record_music_played(self, guild: "Guild"):
        cursor = self.connection.cursor()

        server_id = guild.guild_id
        server_name = guild.guild_name
        
        song = guild.now_playing
        user_name = song.applicant_name
        display_name = song.applicant_displayname
        youtube_url = song.youtube_url
        title = song.title
        duration = song.duration

        try:
            played_at = datetime.datetime.now()
            
            # 1. Songs 테이블에 노래 추가 (중복이면 기존 ID 가져오기)
            cursor.execute(
                """
                INSERT INTO Songs (youtube_url, title, duration)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
            """,
                (youtube_url, title, duration),
            )
            song_id = cursor.lastrowid

            # 2. Users 테이블에 유저 추가 (중복이면 기존 ID 가져오기)
            cursor.execute(
                """
                INSERT INTO Users (name)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
            """,
                (user_name,),
            )
            user_id = cursor.lastrowid

            # 3. Servers 테이블에 서버 추가/업데이트 (없으면 추가, 있으면 업데이트)
            cursor.execute(
                """
                INSERT INTO Servers (server_id, server_name, last_played_song_id, last_played_user_id, last_played_at)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    server_name = VALUES(server_name),
                    last_played_song_id = VALUES(last_played_song_id),
                    last_played_user_id = VALUES(last_played_user_id),
                    last_played_at = VALUES(last_played_at)
            """,
                (server_id, server_name, song_id, user_id, played_at),
            )
            
            # 4. ServerMembers 테이블에 서버-유저 관계 추가 (없을 경우에만)
            cursor.execute(
                """
                INSERT INTO ServerMembers (server_id, user_id, display_name)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE display_name = VALUES(display_name)
            """,
                (server_id, user_id, display_name),
            )

            # 5. PlayHistory에 재생 기록 추가
            cursor.execute(
                """
                INSERT INTO PlayHistory (server_id, song_id, user_id, played_at)
                VALUES (%s, %s, %s, %s)
            """,
                (server_id, song_id, user_id, played_at),
            )

            # 6. DailyPlayStats 업데이트 (해당 날짜의 총 재생 시간 증가)
            today = datetime.date.today()
            cursor.execute(
                """
                INSERT INTO DailyPlayStats (server_id, user_id, date, total_duration)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE total_duration = total_duration + %s
            """,
                (server_id, user_id, today, duration, duration),
            )

            self.connection.commit()
            print({"success": True, "song_id": song_id, "user_id": user_id, "played_at": played_at, "message": "노래 재생 기록이 성공적으로 추가되었습니다."})

        except Exception as e:
            self.connection.rollback()
            print({"success": False, "error": str(e), "message": "노래 재생 기록 추가 중 오류가 발생했습니다."})
        finally:
            cursor.close()


database_insert = DatabaseInsert()

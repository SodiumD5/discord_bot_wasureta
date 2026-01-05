import datetime
from typing import TYPE_CHECKING
from database.database_init import DatabaseInit
from utils.error_controller import report

if TYPE_CHECKING:
    from data.guild import Guild


class DatabaseInsert(DatabaseInit):
    def __init__(self):
        super().__init__()

    def record_music_played(self, guild: "Guild"):
        server_id = guild.id
        server_name = guild.name

        song = guild.now_playing
        user_name = song.applicant_name
        display_name = song.applicant_displayname
        youtube_url = song.youtube_url
        title = song.title
        duration = song.duration
        video_id = song.video_id

        if not self.reconnect():
            return
        try:
            cursor = self.connection.cursor()
            played_at = datetime.datetime.now()

            # 1. Songs 테이블에 노래 추가 (중복이면 무시)
            cursor.execute(
                """
                INSERT INTO Songs (id, youtube_url, title, duration)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    youtube_url = VALUES(youtube_url),
                    title = VALUES(title),
                    duration = VALUES(duration)
                """,
                (video_id, youtube_url, title, duration),
            )

            # 2. Users 테이블에 유저 추가 (중복이면 무시)
            cursor.execute(
                """
                INSERT INTO Users (name)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
                """,
                (user_name,),
            )

            # 3. Servers 테이블에 서버 추가/업데이트 (없으면 추가, 있으면 업데이트)
            cursor.execute(
                """
                INSERT INTO Servers (server_id, server_name)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE 
                    server_name = VALUES(server_name)
                """,
                (server_id, server_name),
            )

            # 4. ServerMembers 테이블에 서버-유저 관계 추가 (없을 경우에만)
            cursor.execute(
                """
                INSERT INTO ServerMembers (server_id, user_name, display_name)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE display_name = VALUES(display_name)
                """,
                (server_id, user_name, display_name),
            )

            # 5. PlayHistory에 재생 기록 추가
            cursor.execute(
                """
                INSERT INTO PlayHistory (server_id, song_id, user_name, played_at)
                VALUES (%s, %s, %s, %s)
                """,
                (server_id, video_id, user_name, played_at),
            )

            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            report.error_record(caller="record_music_played", error=e, is_db_error=True)
        finally:
            cursor.close()

    def update_server_last_play(self, guild: "Guild"):
        server_id = guild.id
        song = guild.now_playing
        user_name = song.applicant_name
        video_id = song.video_id

        if not self.reconnect():
            return
        try:
            cursor = self.connection.cursor()
            played_at = datetime.datetime.now()

            # Servers 테이블의 last_played 필드들 업데이트
            cursor.execute(
                """
                UPDATE Servers 
                SET last_played_song_id = %s,
                    last_played_user_name = %s,
                    last_played_at = %s
                WHERE server_id = %s
                """,
                (video_id, user_name, played_at, server_id),
            )
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            report.error_record(caller="update_server_last_play", error=e, is_db_error=True)
        finally:
            cursor.close()

    def update_user_listen_time(self, user, server_id: int, plus_time: int):
        if not self.reconnect():
            return

        user_name = user.name
        display_name = user.display_name
        try:
            cursor = self.connection.cursor()

            cursor.execute(
                """
                INSERT IGNORE INTO Users (name)
                VALUES (%s)
                """,
                (user_name,),
            )

            cursor.execute(
                """
                INSERT IGNORE INTO ServerMembers (server_id, user_name, display_name)
                VALUES (%s, %s, %s)
                """,
                (server_id, user_name, display_name),
            )

            cursor.execute(
                """
                INSERT INTO DailyPlayStats (server_id, user_name, date, total_duration)
                VALUES (%s, %s, CURDATE(), %s)
                ON DUPLICATE KEY UPDATE total_duration = total_duration + %s
                """,
                (server_id, user_name, plus_time, plus_time),
            )
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            report.error_record(caller="update_user_listen_time", error=e, is_db_error=True)
        finally:
            cursor.close()


database_insert = DatabaseInsert()

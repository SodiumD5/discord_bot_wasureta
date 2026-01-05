from database.database_init import DatabaseInit
from utils.error_controller import report


class DatabaseSearch(DatabaseInit):
    def __init__(self):
        super().__init__()

    def get_last_played_song(self, server_id: int):
        if not self.reconnect():
            return

        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT 
                    s.id,
                    s.youtube_url,
                    s.title,
                    s.duration,
                    srv.last_played_at AS played_at,
                    u.name AS user_name,
                    sm.display_name
                FROM Servers srv
                JOIN Songs s ON srv.last_played_song_id = s.id
                JOIN Users u ON srv.last_played_user_name = u.name
                LEFT JOIN ServerMembers sm ON sm.server_id = srv.server_id 
                    AND sm.user_name = u.name
                WHERE srv.server_id = %s
                """
            cursor.execute(query, (server_id,))
            result = cursor.fetchone()
            self.connection.commit()
            return result
        except Exception as e:
            report.error_record(caller="get_last_played_song", error=e, is_db_error=True)
            return None
        finally:
            cursor.close()

    def get_top_users(self, server_id: int, limit: int = 10):
        if not self.reconnect():
            return

        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT 
                    sm.display_name,
                    u.name AS user_name,
                    COUNT(ph.id) AS play_count
                FROM PlayHistory ph
                JOIN Users u ON ph.user_name = u.name
                LEFT JOIN ServerMembers sm ON sm.server_id = ph.server_id 
                    AND sm.user_name = u.name
                WHERE ph.server_id = %s
                GROUP BY u.name, sm.display_name
                ORDER BY play_count DESC
                LIMIT %s
                """
            cursor.execute(query, (server_id, limit))
            results = cursor.fetchall()
            self.connection.commit()
            return results
        except Exception as e:
            print(f"get_top_players 오류: {e}")
            return None
        finally:
            cursor.close()

    def get_top_songs(self, server_id: int, limit: int = 10):
        if not self.reconnect():
            return

        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT 
                    s.id,
                    s.youtube_url AS url,
                    s.title,
                    s.duration,
                    COUNT(ph.id) AS play_count
                FROM PlayHistory ph
                JOIN Songs s ON ph.song_id = s.id
                WHERE ph.server_id = %s
                GROUP BY s.id, s.youtube_url, s.title, s.duration
                ORDER BY play_count DESC
                LIMIT %s
                """
            cursor.execute(query, (server_id, limit))
            results = cursor.fetchall()
            self.connection.commit()
            return results
        except Exception as e:
            report.error_record(caller="get_top_songs", error=e, is_db_error=True)
            return None
        finally:
            cursor.close()

    def get_top_songs_by_user(self, server_id: int, display_name: str, limit: int = 10):
        if not self.reconnect():
            return

        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT 
                    s.id,
                    s.youtube_url AS url,
                    s.title,
                    s.duration,
                    COUNT(ph.id) AS play_count
                FROM PlayHistory ph
                JOIN Songs s ON ph.song_id = s.id
                JOIN ServerMembers sm ON ph.server_id = sm.server_id 
                                        AND ph.user_name = sm.user_name
                WHERE ph.server_id = %s AND sm.display_name = %s
                GROUP BY s.id, s.youtube_url, s.title, s.duration
                ORDER BY play_count DESC
                LIMIT %s
                """
            cursor.execute(query, (server_id, display_name, limit))
            results = cursor.fetchall()
            self.connection.commit()
            return results
        except Exception as e:
            report.error_record(caller="get_top_songs_by_user", error=e, is_db_error=True)
            return None
        finally:
            cursor.close()


database_search = DatabaseSearch()

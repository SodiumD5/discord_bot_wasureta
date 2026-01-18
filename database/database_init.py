import os, time
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from utils.error_controller import report


class DatabaseInit:
    def __init__(self):
        self.connection = None
        self.last_ping = time.time()
        self._connect()

    def _connect(self):
        """MySQL 데이터베이스 연결"""
        try:
            load_dotenv()
            MYSQL_HOST = os.getenv(key="MYSQL_HOST", default="localhost")  # 로컬에선 default로 씀
            MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
            self.connection = mysql.connector.connect(
                host=MYSQL_HOST,
                user="root",
                password=MYSQL_PASSWORD,
                database="wasureta",
                autocommit=False,
                pool_name="wasureta_pool",
                pool_size=5,
            )

            if self.connection.is_connected():
                cursor = self.connection.cursor()
                cursor.execute(
                    """
                    CREATE DATABASE IF NOT EXISTS wasureta 
                    CHARACTER SET utf8mb4 
                    COLLATE utf8mb4_unicode_ci
                    """
                )
                cursor.execute("USE wasureta")
                cursor.close()
            return True
        except Error as e:
            report.error_record(caller="DB_connect", error=e, is_db_error=True)
            return False

    def reconnect(self):
        try:
            if not self.connection or not self.connection.is_connected():
                return self._connect()

            if time.time() - self.last_ping > 600:
                self.connection.ping(reconnect=True)
                self.last_ping = time.time()

            return True
        except Error:
            return self._connect()

    def create_tables(self):
        """테이블 생성"""
        if not self.connection:
            return

        cursor = self.connection.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        tables = {}

        # Songs 테이블
        tables[
            "Songs"
        ] = """
        CREATE TABLE IF NOT EXISTS Songs (
            id VARCHAR(20) PRIMARY KEY COMMENT 'YouTube 비디오 ID',
            youtube_url VARCHAR(255) UNIQUE NOT NULL,
            title VARCHAR(500) NOT NULL,
            duration INT NOT NULL COMMENT 'seconds',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_youtube_url (youtube_url),
            INDEX idx_title (title)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        # Users 테이블 - name을 PK로 변경
        tables[
            "Users"
        ] = """
        CREATE TABLE IF NOT EXISTS Users (
            name VARCHAR(255) PRIMARY KEY COMMENT '사용자 고유 식별자',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        # Servers 테이블 - user_id 대신 user_name 사용
        tables[
            "Servers"
        ] = """
        CREATE TABLE IF NOT EXISTS Servers (
            server_id BIGINT PRIMARY KEY COMMENT '서버 고유 식별자',
            server_name VARCHAR(255) NOT NULL COMMENT '서버 이름',
            last_played_song_id VARCHAR(20),
            last_played_user_name VARCHAR(255),
            last_played_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (last_played_song_id) REFERENCES Songs(id) ON DELETE SET NULL,
            FOREIGN KEY (last_played_user_name) REFERENCES Users(name) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        # ServerMembers 테이블 - user_id 대신 user_name 사용
        tables[
            "ServerMembers"
        ] = """
        CREATE TABLE IF NOT EXISTS ServerMembers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            server_id BIGINT NOT NULL,
            user_name VARCHAR(255) NOT NULL,
            display_name VARCHAR(255) NOT NULL COMMENT '해당 서버에서의 사용자 표시 이름',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY idx_server_user (server_id, user_name),
            INDEX idx_server_id (server_id),
            INDEX idx_user_name (user_name),
            FOREIGN KEY (server_id) REFERENCES Servers(server_id) ON DELETE CASCADE,
            FOREIGN KEY (user_name) REFERENCES Users(name) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        # PlayHistory 테이블 - user_id 대신 user_name 사용
        tables[
            "PlayHistory"
        ] = """
        CREATE TABLE IF NOT EXISTS PlayHistory (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            server_id BIGINT NOT NULL,
            song_id VARCHAR(20) NOT NULL,
            user_name VARCHAR(255) NOT NULL,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            INDEX idx_server_played_at (server_id, played_at),
            INDEX idx_server_song (server_id, song_id),
            INDEX idx_server_user (server_id, user_name),
            INDEX idx_user_played_at (user_name, played_at),
            INDEX idx_song_id (song_id),
            FOREIGN KEY (server_id) REFERENCES Servers(server_id) ON DELETE CASCADE,
            FOREIGN KEY (song_id) REFERENCES Songs(id) ON DELETE CASCADE,
            FOREIGN KEY (user_name) REFERENCES Users(name) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        # DailyPlayStats 테이블 - user_id 대신 user_name 사용
        tables[
            "DailyPlayStats"
        ] = """
        CREATE TABLE IF NOT EXISTS DailyPlayStats (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            server_id BIGINT NOT NULL,
            user_name VARCHAR(255) NOT NULL,
            date DATE NOT NULL COMMENT '재생 날짜',
            total_duration INT NOT NULL DEFAULT 0 COMMENT '해당 날짜의 총 재생 시간(초)',
            UNIQUE INDEX idx_server_user_date (server_id, user_name, date),
            INDEX idx_server_date (server_id, date),
            INDEX idx_user_date (user_name, date),
            FOREIGN KEY (server_id) REFERENCES Servers(server_id) ON DELETE CASCADE,
            FOREIGN KEY (user_name) REFERENCES Users(name) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        # 테이블 생성 실행
        for table_name, create_statement in tables.items():
            try:
                cursor.execute(create_statement)
                print(f"{table_name} 테이블 생성 완료")
            except Error as e:
                print(f"{table_name} 테이블 생성 실패: {e}")

        # 외래키 제약조건 체크 활성화
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        self.connection.commit()
        cursor.close()
        print("\n모든 테이블 생성 완료!")

    def show_tables(self):
        """생성된 테이블 목록 확인"""
        if not self.connection:
            return

        cursor = self.connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        print("\n=== 생성된 테이블 목록 ===")
        for table in tables:
            print(f"- {table[0]}")
        print()
        cursor.close()

    def drop_tables(self):
        """모든 테이블 삭제"""
        if not self.connection:
            return

        cursor = self.connection.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

        # 삭제할 테이블 목록
        tables = ["DailyPlayStats", "PlayHistory", "ServerMembers", "Servers", "Users", "Songs"]

        print("\n=== 테이블 삭제 시작 ===")
        for table_name in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                print(f"{table_name} 테이블 삭제 완료")
            except Error as e:
                print(f"{table_name} 테이블 삭제 실패: {e}")

        # 외래키 제약조건 체크 활성화
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        self.connection.commit()
        cursor.close()
        print("\n모든 테이블 삭제 완료!\n")

    def database_init(self):
        if self.connection:
            self.create_tables()
            self.show_tables()
            self.connection.close()


setting = DatabaseInit()

if __name__ == "__main__":
    DBsetting = DatabaseInit()
    # DBsetting.drop_tables()
    DBsetting.database_init()

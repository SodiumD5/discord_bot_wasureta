import pymysql
import os
from dotenv import load_dotenv
from prettytable import PrettyTable

#기본세팅
def run_sql():
    load_dotenv()
    ID = os.getenv("ID")
    PW = os.getenv("PW")

    #연결
    connect = pymysql.connect(
        host = "127.0.0.1",
        user = ID,
        password = PW,
        port = 3306
    )

    #커서 생성
    cursor = connect.cursor()

    #schema 지정
    cursor.execute("USE wasureta;")

    return connect, cursor

#데이터 추가하기
def add_data(cursor,guild_id, user_name, song_name):
    #guild table에 값 변경
    cursor.execute(f"""INSERT INTO guild (guild_id, song_name, repeated, update_date) VALUES(%s, %s, 1, NOW())
                   ON DUPLICATE KEY UPDATE repeated = repeated+1;""",
                   (guild_id, song_name))
    #users table에 값 변경
    cursor.execute(f"""INSERT INTO users (guild_id, user_name, song_name, repeated, update_date) VALUES(%s, %s, %s, 1, NOW())
                   ON DUPLICATE KEY UPDATE repeated = repeated+1, update_date = NOW();""",
                   (guild_id, user_name, song_name))
    cursor.execute("SELECT * from users")
    
#결과 보여주기
def show_result(cursor):
    databases = cursor.fetchall()
    table = PrettyTable()
    table.field_names = [data[0] for data in cursor.description]

    for row in databases:
        table.add_row(row)
    
    print(table)

#연결 종료 (연결의 효율성을 위해)
def disconnect_sql(connect, cursor):
    connect.commit()
    cursor.close()
    connect.close()

#이걸 호출하면, update해줌.
def update_sql(guild_id, user_name, song_name):
    connect, cursor = run_sql()
    add_data(cursor,guild_id, user_name, song_name)
    show_result(cursor)
    disconnect_sql(connect, cursor)


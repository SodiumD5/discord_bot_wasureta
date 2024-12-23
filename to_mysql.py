import pymysql
import os
from dotenv import load_dotenv
from prettytable import PrettyTable
import random

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
    cursor.execute("""INSERT INTO guild (guild_id, song_name, repeated, update_date) VALUES(%s, %s, 1, NOW())
                   ON DUPLICATE KEY UPDATE repeated = repeated+1;""",
                   (guild_id, song_name))
    #users table에 값 변경
    cursor.execute("""INSERT INTO users (guild_id, user_name, song_name, repeated, update_date) VALUES(%s, %s, %s, 1, NOW())
                   ON DUPLICATE KEY UPDATE repeated = repeated+1, update_date = NOW();""",
                   (guild_id, user_name, song_name))
    cursor.execute("SELECT * from users")

#결과 찾기
def select_guild_data(cursor, guild_id, limit, start_column):
    cursor.execute("""SELECT * FROM wasureta.guild WHERE guild_id = %s ORDER BY repeated DESC LIMIT %s OFFSET %s;""", #LIMIT는 개수, OFFSET은 시작 행번호호
                   (guild_id, limit, start_column)) #반드시 튜플로 해야함
    result = cursor.fetchall()

    return result

def select_users_data(cursor, guild_id, user_name, limit, start_column):
    cursor.execute("""SELECT * FROM wasureta.users WHERE guild_id = %s AND user_name = %s ORDER BY repeated DESC LIMIT %s OFFSET %s;""", 
                   (guild_id, user_name, limit, start_column)) #반드시 튜플로 해야함
    result = cursor.fetchall()

    return result

def select_music_data(cursor, guild_id, song_name):
    cursor.execute("""SELECT * FROM wasureta.guild WHERE guild_id = %s AND song_name = %s""", (guild_id, song_name))
    result = cursor.fetchall()

    return result

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

#이걸 호출하면, add해줌
def add_sql(guild_id, user_name, song_name):
    connect, cursor = run_sql()
    add_data(cursor,guild_id, user_name, song_name)
    #show_result(cursor)
    disconnect_sql(connect, cursor)

def rank(guild_id):
    connect, cursor = run_sql()
    result = select_guild_data(cursor, guild_id, 10, 0)
    disconnect_sql(connect, cursor)
    return result

def find_user(guild_id, user_name):
    connect, cursor = run_sql()
    result = select_users_data(cursor, guild_id, user_name, 10, 0)
    disconnect_sql(connect, cursor)
    return result

def find_music(guild_id, song_name):
    connect, cursor = run_sql()
    result = select_music_data(cursor, guild_id, song_name)
    disconnect_sql(connect, cursor)
    return result

def random_user_playlist(guild_id, user_name, start_num, end_num):
    connect, cursor = run_sql()
    start_num -= 1
    end_num -= 1
    #유저이름이 없는 경우, 서버에서 찾음음
    if user_name == None:
        result = select_guild_data(cursor, guild_id, end_num-start_num+1, start_num)
    else:
        result = select_users_data(cursor, guild_id, user_name, end_num-start_num+1, start_num)
    disconnect_sql(connect, cursor)
    
    sample = random.sample(result, min(10, len(result)))
    return sample


def save_title_data(title, link):
    connect, cursor = run_sql()
    # 없으면 저장. 있는지 확인
    cursor.execute("""SELECT * FROM title WHERE title = %s""", (title))
    is_data_in = cursor.fetchall()

    if is_data_in == ():
        cursor.execute("""INSERT INTO title (title, link) VALUES(%s, %s);""", (title, link))
    disconnect_sql(connect, cursor)

def find_title_data(url):
    connect, cursor = run_sql()
    cursor.execute("""SELECT * FROM title WHERE url = %s""", (url))
    result = cursor.fetchall()
    disconnect_sql(connect, cursor)

    return result

def find_url_data(title):
    connect, cursor = run_sql()
    cursor.execute("""SELECT * FROM title WHERE title = %s""", (title))
    result = cursor.fetchall()
    disconnect_sql(connect, cursor)

    return result
    
    
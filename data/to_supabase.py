import os
from dotenv import load_dotenv
import random

from supabase import create_client
from datetime import datetime

#기본세팅
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

#users테이블 관련
def add_sql(server_id, user_name, song_name): #데이터 추가하기
    #조회하기
    result = supabase.table('users').select('repeated').eq('server_id', server_id).eq('user_name', user_name).eq('song_name', song_name).limit(1).execute()
    if result.data: #존재할 경우 증가시키기
        current_repeated = result.data[0]['repeated']
        supabase.table('users').update({
            'repeated': current_repeated + 1,
            'date': datetime.now().isoformat()
        }).eq('server_id', server_id).eq('user_name', user_name).eq('song_name', song_name).execute()
        
    else: #없으면 새로 삽입
        supabase.table('users').insert({
            'server_id': server_id,
            'user_name': user_name,
            'song_name': song_name,
            'repeated': 1,
            'date': datetime.now().isoformat()
        }).execute()

def server_song_ranking(server_id): #서버 전체 재생 순위
    top_data = supabase.rpc("show_server_ranking", {
        "p_server_id": server_id,
        "p_limit" : 10,
        "p_start_index" : 0
    }).execute()
    
    info = supabase.rpc("get_server_rank", {
        "p_server_id": server_id,
    }).execute()

    return top_data.data, info.data[0]

def user_song_ranking(server_id, user_name): #각 유저의 재생 순위    
    top_data = supabase.rpc("show_server_ranking", {
        "p_server_id": server_id,
        "p_limit" : 10,
        "p_start_index" : 0
    }).execute()
    
    info = supabase.rpc("get_user_rank", {
        "p_server_id": server_id,
        "p_user_name": user_name
    }).execute()

    return top_data.data, info.data[0]

def random_user_playlist(server_id, user_name, start_num, end_num): #그 사람이름으로 랜덤 플리 생성
    if user_name == None: #유저이름이 없는 경우, 서버로 대체
        response = supabase.rpc("make_server_playlist", {
        "p_server_id": server_id,
        "p_limit" : end_num-start_num+1,
        "p_start_index" : start_num-1
        }).execute()
    else:
        response = supabase.rpc("make_user_playlist", {
        "p_server_id": server_id,
        "p_user_name": user_name,
        "p_limit" : end_num-start_num+1,
        "p_start_index" : start_num-1
        }).execute()
    
    sample = random.sample(response.data, min(10, len(response.data)))
    return sample

def find_music(server_id, song_name): #해당 노래의 재생 횟수
    response = supabase.rpc("find_music", {
        "p_server_id" : server_id,
        "p_song_name" : song_name
    }).execute()
    
    return response.data

def show_server_ranking(server_id):
    response = supabase.rpc("show_server_ranking",{
        "p_server_id" : server_id
    }).execute()
    return response.data

#title 테이블 관련
def save_title_data(title, link, duration):
    response = supabase.table("title").select("*").eq("title", title).execute()
    if not response.data:
        supabase.table("title").insert({"title" : title, "link" : link, "duration" : duration}).execute()

def find_url_data(title):
    response = supabase.table("title").select("*").eq("title", title).execute()
    return response.data

#last_play 테이블 관련
def search_lastplay(server_id):
    response = supabase.table("last_play").select("*").eq("server_id", server_id).execute()
    return response.data

def update_lastplay(server_id, title, link, duration):
    data = {"server_id" : server_id, "title" : title, "link" : link, "date": datetime.now().isoformat(), "duration": duration}
    supabase.table("last_play").upsert(data, on_conflict="server_id").execute() 
    
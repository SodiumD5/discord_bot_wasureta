# Wasureta 
discord bot 개발 중
음악 재생을 하는데, 각 서버마다 틀어진 노래의 순위를 저장해둔다. 
since 2024.11.01

### 제작자: nacl12

기본적으로 음악 봇이며, 대형 음악 봇에서 부족했던 기능을 추가하자는 취지로 제작되었습니다.  
**`/명령어`** 와 **`!명령어`** 를 모두 지원하지만, **`/명령어`** 사용을 권장합니다. (인자를 명시하지 않아 혼동을 줄일 수 있기 때문입니다.)

---

## 기본 기능 (Basic)

### 1. `—-`
- 파란선을 그어줍니다.  
  (대화의 흐름을 전환할 때 사용)

### 2. `ping`
- 봇의 핑 상태를 확인합니다.

---

## 유튜브 기능 (Music Playback)

> 괄호 안의 내용은 인자가 필요함을 의미합니다.

### 1. `play (링크/검색어)`
- **유튜브 링크**: 해당 링크의 노래를 재생목록에 추가합니다.
- **검색어**: 검색 결과 상위 5개의 곡을 버튼으로 보여주며, 선택 후 대기열에 추가 가능합니다.
- **유튜브 플레이리스트 링크**: 최대 50곡까지 재생목록에 추가합니다.
- 통화방에 들어가서 명령어를 사용해야 합니다.

### 2. `que`
- 현재 대기열의 목록을 10개씩 표시합니다.
- **이전/다음 페이지 버튼**으로 탐색 가능하며, 제거 버튼으로 곡을 삭제할 수 있습니다.

### 3. `now-playing`
- 현재 재생 중인 노래의 제목과 링크를 표시합니다.

### 4. `skip`
- 현재 곡을 중단하고 다음 곡을 재생합니다.

### 5. `pause`
- 곡을 일시 중지하거나, 중지 상태에서 다시 재생합니다.

### 6. `search-server-top10`
- 서버 내에서 가장 많이 재생된 상위 10곡을 보여줍니다.
- **하단 버튼**으로 즉시 대기열에 추가 가능합니다.

### 7. `search-user-top10 (유저아이디)`
- 특정 사용자가 가장 많이 재생한 상위 10곡을 보여줍니다.  
  (유저아이디 입력이 없을 경우 자신의 기록을 표시)
- **하단 버튼**으로 즉시 대기열에 추가 가능합니다.

### 8. `how-many-played (검색어/노래 제목)`
- 입력한 검색어/노래 제목이 서버에서 몇 번 재생되었는지 조회합니다.
- **정확한 제목 복사**를 권장하며, 하단 버튼으로 재생 가능합니다.

### 9. `leave`
- 봇을 음성 채널에서 퇴장시킵니다.  
  (대기열 초기화)

### 10. `refresh-que`
- 대기열을 초기화합니다.

### 11. `playlist (유저아이디) (시작 번호) (끝 번호)`
- 서버/유저의 재생 순위에서 10곡을 랜덤으로 골라 플레이리스트 생성.
- 전체 또는 단일 곡을 대기열에 추가할 수 있습니다.
- 기본값:
  - 유저아이디 입력이 없으면 서버 내 데이터를 사용
  - 시작 번호 없으면 1위부터, 끝 번호 없으면 50위까지 검색

### 12. `repeat`
- 버튼을 통해 다음 중 하나를 선택:
  - 현재 곡 무한 반복
  - 대기열 무한 반복
  - 반복 끄기

### 13. `wasu`
- Wasureta 원곡을 대기열 최상단(1번)으로 이동합니다.

### 14. `gd`
- 신원 미상의 **지메 플레이 영상**을 재생합니다.

---

### requirements

pip install Flask discord python-dotenv yt-dlp pymysql PrettyTable asyncio
pip install pyNaCl
pip install cryptography (우분투에서)
ffmpeg를 다운 받아야한다. 
sudo apt install ffmpeg -y
env 파일 생성 : nano .env
자신의 ffmpeg 경로로 경로를 세팅해준다. 
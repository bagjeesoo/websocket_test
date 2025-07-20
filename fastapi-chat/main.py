from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, status, Query, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import jwt
from passlib.context import CryptContext
import pymysql
from jwt_helper import create_access_token, verify_token
from dotenv import load_dotenv
import os
import redis

load_dotenv()
# docker-compose.yml의 서비스명이 redis이면
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 간단한 사용자 저장 (실제로는 DB 쿼리로!)
fake_users_db = {}

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 1. 연결된 웹소켓 클라이언트들 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        # 해당 room에 리스트가 없다면 먼저 만듦
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections:
            try:
                self.active_connections[room].remove(websocket)
                # 아무도 남지 않았을 경우 방(리스트)을 아예 삭제할 수도 있음(선택)
                if not self.active_connections[room]:
                    del self.active_connections[room]
            except ValueError:
                pass  # 이미 없으면 무시

    async def broadcast(self, message: str, room: str):
        connections = self.active_connections.get(room, [])
        for connection in connections:
            await connection.send_text(message)

manager = ConnectionManager()

# 웹 채팅 페이지
@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    
    return templates.TemplateResponse("chat.html", {"request": request})

# 웹소켓 핸들러 
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...), room: str = Query("default")):
    # token = websocket.query_params.get("token")
    # 1. JWT 토큰 검증
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        print("🟢 JWT payload:", payload)
        if username is None:
            raise ValueError("No username in token")
    except Exception as e:
        print("❌ JWT 검증 실패:", e)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return    

    # 2. 채팅방 key 설정
    chat_key = f"chatlog:{room}"

    # ✅ 먼저 websocket 연결 수락
    await manager.connect(websocket, room)
    

    # 3. 연결 즉시, 최큰 메세지 100개 보내기
    recent_msgs = redis_client.lrange(chat_key, -100, -1)
    for msg in recent_msgs:
        await websocket.send_text(msg)

    # 4. 브로드캐스트 및 케세지 기록    
    
    await manager.broadcast(f"✅ {username}님이 [{room}] 채팅방에 입장했습니다.", room)

    try:
        while True:
            data = await websocket.receive_text()
            msg = f"{username}: {data}"
            redis_client.rpush(chat_key, msg)
            # 한 방에 500개만 유지
            redis_client.ltrim(chat_key, -500, -1)
            await manager.broadcast(msg, room)  # 방에 뿌림 
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        await manager.broadcast(f"❌ {username}님이 퇴장했습니다.", room)




@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# 회원가입
@app.post("/register")
async def register(id: str = Form(...), password: str = Form(...)):

    # db연결
    conn = pymysql.connect(host="mysql", user="testuser", password="testpass", port=3306, database="mydb", charset="utf8mb4")

    cursor = conn.cursor()

    try:
        # 아이디 중복확인
        sql = 'SELECT * FROM user WHERE id = %s'
        cursor.execute(sql, (id,))
        existing = cursor.fetchone()
        if existing:
            return {"error": "이미 존재하는 사용자입니다."}
        
        # 비밀번호 해싱
        hashed_pw = pwd_context.hash(password)

        # 사용자 등록
        insert_sql = "INSERT INTO user VALUES(%s, %s)"
        cursor.execute(insert_sql, (id, hashed_pw))
        conn.commit()
    except Exception as e:
        print(f"회원가입 실패 {e}")
    finally:
        conn.close()

    return RedirectResponse(url="/login", status_code=302)

# 로그인 페이지
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 로그인 기능
@app.post("/login")
async def login(id: str = Form(...), password: str = Form(...)):

    conn = pymysql.connect(host="mysql", user="testuser", password="testpass", port=3306, database="mydb", charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)

    cursor = conn.cursor()

    try:
        login_sql = 'SELECT * FROM user WHERE id = %s'

        cursor.execute(login_sql, (id,))
        user = cursor.fetchone()

        if not user:
            return {"error":"존재하지 않는 사용자입니다."}
        
        # 비밀번호 비교
        if pwd_context.verify(password, user["password"]):
            # ✅ JWT 토큰 생성
            token = create_access_token({"sub": id})
            conn.commit()
        
            # ✅ 토큰을 응답으로 전달 (방법 1: JSON)
            return JSONResponse(content={
                "access_token": token,
                "token_type": "bearer",
                "message": f"{id}님 로그인 성공!",
                "sub": id
            })
        else:
            return {"error": "비밀번호가 일치하지 않습니다."}

    except Exception as e:
        print(f'로그인 실패이유 : {e}')
        return HTMLResponse("서버 오류가 발생했습니다.", status_code=500)
    finally:
        conn.close()
    

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})
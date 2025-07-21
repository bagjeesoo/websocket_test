# 🟦 user_manager.py

from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # 현재 접속 중인 유저 ID 목록
        self.online_users: set[str] = set()
        # 방별 웹소켓 연결
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str, username: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)
        self.online_users.add(username)

    def disconnect(self, websocket: WebSocket, room: str, username: str):
        if room in self.active_connections:
            try:
                self.active_connections[room].remove(websocket)
                if not self.active_connections[room]:  # 아무도 없으면 삭제
                    del self.active_connections[room]
            except ValueError:
                pass
        self.online_users.discard(username)

    async def broadcast(self, message: str, room: str):
        connections = self.active_connections.get(room, [])
        for connection in connections:
            await connection.send_text(message)

    def get_online_users(self):
        return list(self.online_users)

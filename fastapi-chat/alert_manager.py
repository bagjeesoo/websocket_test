from fastapi import WebSocket
from typing import DefaultDict
from collections import defaultdict

# 알림 전송 별도 관리자
class AlertManager:
    def __init__(self):
        # Key: 사용자 ID, Value: 연결된 WebSocket 리스트
        self.connections: DefaultDict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.connections:
            try:
                self.connections[user_id].remove(websocket)
            except ValueError:
                pass

    async def send_alert(self, to_user_id: str, from_user_id: str, message: str):
        for ws in self.connections.get(to_user_id, []):
            await ws.send_json({
                "from": from_user_id,
                "message": message
            })

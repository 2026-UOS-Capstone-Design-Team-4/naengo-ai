from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatRoom


class AdminChatRoomNotFoundError(Exception):
    pass


class AdminChatRoomService:
    def __init__(self, db: Session):
        self.db = db

    def hard_delete_room(self, room_id: int) -> None:
        room = self.db.get(ChatRoom, room_id)
        if room is None:
            raise AdminChatRoomNotFoundError(room_id)

        self.db.query(ChatMessage).filter(ChatMessage.room_id == room_id).delete(
            synchronize_session=False
        )
        self.db.delete(room)
        self.db.commit()

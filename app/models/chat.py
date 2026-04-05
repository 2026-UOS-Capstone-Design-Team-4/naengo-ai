from sqlalchemy import (
    BOOLEAN,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    room_id = Column(String(100), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), default="새로운 레시피 상담")
    is_active = Column(BOOLEAN, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계 설정
    user = relationship("User", back_populates="chat_rooms")
    sessions = relationship("SessionLog", back_populates="room")


class SessionLog(Base):
    __tablename__ = "session_logs"

    session_id = Column(String(100), primary_key=True)
    room_id = Column(String(100), ForeignKey("chat_rooms.room_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    
    # AI 분석 데이터
    extracted_ingredients = Column(JSONB)
    user_feedback = Column(JSONB)
    recommended_recipe_ids = Column(ARRAY(Integer))
    selected_recipe_id = Column(Integer, ForeignKey("recipes.recipe_id"))
    chat_messages = Column(JSONB)
    
    status = Column(String(20), default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED, ABORTED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계 설정
    room = relationship("ChatRoom", back_populates="sessions")

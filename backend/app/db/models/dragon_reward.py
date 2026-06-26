from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DragonReward(Base):
    __tablename__ = "dragon_rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reward_date: Mapped[date] = mapped_column(Date, nullable=False)
    milestone: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    color: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="dragon_rewards")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "reward_date",
            "milestone",
            name="uq_dragon_rewards_user_date_milestone",
        ),
    )

"""用户、班级与学生班级关系模型。"""
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UserRole


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default=UserRole.STUDENT)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    taught_classes: Mapped[list["ClassRoom"]] = relationship(back_populates="teacher")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")


class ClassRoom(TimestampMixin, Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    teacher: Mapped[User] = relationship(back_populates="taught_classes")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="classroom")


class Enrollment(TimestampMixin, Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_enrollment_class_student"),
        Index("ix_enrollments_student_class", "student_id", "class_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    classroom: Mapped[ClassRoom] = relationship(back_populates="enrollments")
    student: Mapped[User] = relationship(back_populates="enrollments")
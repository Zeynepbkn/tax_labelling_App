from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.security import MAX_BCRYPT_PASSWORD_BYTES, hash_password, verify_password
from app.db.models.user import User, UserRole


NAME_SEPARATOR_CHARS = {"-", "'", "."}


def normalize_full_name(value: str) -> str:
    return " ".join((value or "").strip().split())


def is_valid_person_full_name(value: str) -> bool:
    parts = normalize_full_name(value).split(" ")
    if len(parts) < 2:
        return False

    for part in parts:
        letters = [char for char in part if char.isalpha()]
        if len(letters) < 2:
            return False
        if any(not (char.isalpha() or char in NAME_SEPARATOR_CHARS) for char in part):
            return False

    return True


def is_email_login(value: str) -> bool:
    return "@" in value and "." in value.rsplit("@", 1)[-1]


def missing_user_message(username_or_email: str) -> str:
    lowered = username_or_email.lower()
    if is_email_login(lowered):
        if lowered.endswith("@gmail.com") or lowered.endswith("@googlemail.com"):
            return "Bu Gmail adresine ait kullanıcı yok."
        return "Bu email adresine ait kullanıcı yok."
    return "Böyle bir kullanıcı yok."


def create_user(db: Session, kullanici_adi: str, email: str, password: str) -> User:
    kullanici_adi = normalize_full_name(kullanici_adi)
    email = email.strip().lower()
    if not is_valid_person_full_name(kullanici_adi):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kullanıcı adı gerçek ad ve soyad şeklinde girilmelidir.",
        )
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Şifre en fazla 72 byte olabilir. Lütfen daha kısa bir şifre kullanın.",
        )

    email_exists = db.execute(
        select(User.id).where(func.lower(User.email) == email)
    ).scalar_one_or_none()
    if email_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu mail adresi ile kayıt oluşturulmuş, lütfen başka bir mail adresi belirleyin.",
        )

    username_exists = db.execute(
        select(User.id).where(User.kullanici_adi == kullanici_adi)
    ).scalar_one_or_none()
    if username_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu kullanıcı adı zaten kayıtlı, lütfen farklı bir ad soyad girin.",
        )

    user = User(
        kullanici_adi=kullanici_adi,
        email=email,
        hashed_password=hash_password(password),
        role=UserRole.labeler,
        exam_passed=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username_or_email: str, password: str) -> User:
    username_or_email = normalize_full_name(username_or_email)
    lookup = username_or_email.lower() if is_email_login(username_or_email) else username_or_email
    user = db.execute(
        select(User).where(
            or_(
                func.lower(User.email) == lookup.lower(),
                func.lower(User.kullanici_adi) == username_or_email.lower(),
            )
        )
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=missing_user_message(username_or_email))
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Şifre hatalı.")
    return user


def login_and_issue_token(db: Session, username_or_email: str, password: str) -> tuple[str, User]:
    user = authenticate_user(db, username_or_email, password)
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=str(user.id))
    return token, user

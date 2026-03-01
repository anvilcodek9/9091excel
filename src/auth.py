"""네이버 커머스 API OAuth2 인증 토큰 자동 발급.

커머스API 인증 규격(Client Credentials Grant, 전자서명)에 따라
client_id/client_secret으로 액세스 토큰을 발급합니다.
"""

import base64
import time
from typing import Optional
from urllib.parse import urlencode

import bcrypt
import requests

from .exceptions import NaverAPIError

TOKEN_URL = "https://api.commerce.naver.com/external/v1/oauth2/token"
GRANT_TYPE = "client_credentials"
TYPE_SELF = "SELF"


def _is_ascii(value: str) -> bool:
    try:
        value.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _validate_client_secret(client_secret: str) -> str:
    """기본 형식 검증으로 쉘 변수 확장/잘못된 붙여넣기를 빠르게 감지."""
    secret = client_secret.strip()
    if len(secret) < 20:
        raise ValueError(
            "NAVER_CLIENT_SECRET 값이 비정상적으로 짧습니다. "
            "zsh/bash에서 '$' 문자가 확장되어 값이 깨졌을 수 있습니다. "
            "단일 따옴표로 다시 설정하세요: export NAVER_CLIENT_SECRET='your_secret'"
        )
    return secret


def _make_client_secret_sign(client_id: str, client_secret: str, timestamp: int) -> str:
    """전자서명 생성: password = client_id_timestamp, bcrypt(salt=client_secret), Base64."""
    password = f"{client_id}_{timestamp}"
    try:
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            client_secret.encode("utf-8"),
        )
    except ValueError as e:
        raise ValueError(
            "NAVER_CLIENT_SECRET 형식이 올바르지 않습니다. "
            "커머스API 센터에서 발급된 원본 시크릿을 공백/따옴표 없이 그대로 사용하세요."
        ) from e
    return base64.b64encode(hashed).decode("utf-8")


def get_access_token(client_id: str, client_secret: str) -> str:
    """
    client_id와 client_secret으로 네이버 커머스 API 액세스 토큰을 발급합니다.

    공식 문서: Client Credentials Grant, 전자서명(bcrypt + Base64) 사용.
    발급된 토큰 유효시간은 3시간(10,800초)입니다.

    Args:
        client_id: 애플리케이션 ID (커머스API센터에서 발급)
        client_secret: 애플리케이션 시크릿 (bcrypt salt로 사용)

    Returns:
        발급된 access_token 문자열

    Raises:
        NaverAPIError: 토큰 발급 요청 실패 시 (4xx/5xx, 네트워크 오류)
    """
    timestamp = int(time.time() * 1000)
    client_secret_sign = _make_client_secret_sign(client_id, client_secret, timestamp)

    payload = {
        "client_id": client_id,
        "timestamp": timestamp,
        "client_secret_sign": client_secret_sign,
        "grant_type": GRANT_TYPE,
        "type": TYPE_SELF,
    }
    # UTF-8로 인코딩해 전송 (latin-1 기본값 때문에 한글 등 비ASCII 문자 오류 방지)
    body = urlencode(payload, encoding="utf-8")
    body_bytes = body.encode("utf-8")

    try:
        response = requests.post(
            TOKEN_URL,
            data=body_bytes,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        raise NaverAPIError(
            f"토큰 발급 요청 실패: {e}",
            status_code=None,
            response_body=None,
        ) from e

    if not response.ok:
        raise NaverAPIError(
            f"토큰 발급 실패 (HTTP {response.status_code})",
            status_code=response.status_code,
            response_body=response.text,
        )

    data = response.json()
    access_token = data.get("access_token") if isinstance(data, dict) else None
    if not access_token:
        raise NaverAPIError(
            "토큰 발급 응답에 access_token이 없습니다.",
            status_code=response.status_code,
            response_body=response.text,
        )
    return access_token


def resolve_access_token(
    access_token: Optional[str],
    client_id: Optional[str],
    client_secret: Optional[str],
) -> str:
    """
    전달된 토큰이 있으면 그대로 반환하고, 없으면 client_id/secret으로 발급해 반환합니다.

    Args:
        access_token: 이미 가진 액세스 토큰 (있으면 사용)
        client_id: 애플리케이션 ID (토큰 없을 때 발급용)
        client_secret: 애플리케이션 시크릿 (토큰 없을 때 발급용)

    Returns:
        사용할 access_token

    Raises:
        ValueError: 토큰도 없고 client_id/secret으로 발급할 수 없을 때
    """
    if access_token and access_token.strip():
        token = access_token.strip()
        # 잘못 설정된 NAVER_ACCESS_TOKEN(한글/공백 포함)으로 Authorization 헤더 인코딩 에러 방지
        if _is_ascii(token) and (" " not in token) and ("\n" not in token) and ("\r" not in token):
            return token
        # 비정상 토큰은 무시하고 client_id/secret 자동 발급으로 폴백
    if client_id and client_secret and client_id.strip() and client_secret.strip():
        normalized_secret = _validate_client_secret(client_secret)
        return get_access_token(client_id.strip(), normalized_secret)
    raise ValueError(
        "액세스 토큰을 사용할 수 없습니다. "
        "다음 중 하나를 설정하세요: "
        "1) access_token 인자 또는 NAVER_ACCESS_TOKEN 환경 변수(ASCII 토큰), "
        "2) NAVER_CLIENT_ID + NAVER_CLIENT_SECRET 환경 변수(자동 발급)"
    )

from http.client import HTTPResponse

from aiohttp.web import HTTPFound
from aiohttp.web_exceptions import HTTPOk
from src.settings import settings
from init import log

ACCESS_TOKEN_COOKIE_NAME = "access_token"
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
DOMAIN_NAME = settings.domain_name


def set_cookie_and_redirect(redirect: str | None, access_token: str, refresh_token: str):
    """Set cookies and redirect to the specified URL"""
    log.debug("redirect", redirect)
    if redirect:
        response = HTTPFound(redirect)
    else:
        response = HTTPOk()
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        access_token,
        httponly=True,
        secure=True,
        samesite="None",
        domain=DOMAIN_NAME,
        path="/"
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=True,
        samesite="None",
        domain=DOMAIN_NAME,
        path="/"
    )
    return response

def delete_cookies():
    response = HTTPOk()
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        "",
        max_age=0,
        expires="Thu, 01 Jan 1970 00:00:00 GMT",
        domain=DOMAIN_NAME,
        path="/"
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        "",
        max_age=0,
        expires="Thu, 01 Jan 1970 00:00:00 GMT",
        domain=DOMAIN_NAME,
        path="/"
    )
    return response
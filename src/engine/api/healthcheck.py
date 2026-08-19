

from .common import PlainTextResponse, Request


def health_check(req: Request) -> PlainTextResponse:
    '''
    Health Check API

    Return:
    PlainTextResponse with message \"Health check successed\"
    '''

    return PlainTextResponse("Health check successed")

__all__ = [
    "health_check",
]
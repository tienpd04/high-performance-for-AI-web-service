

from .common import Response, Request


def health_check(req: Request) -> Response:
    '''
    Health Check API

    Return:
    Response with status code 200
    '''

    return Response()

__all__ = [
    "health_check",
]
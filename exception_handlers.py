from flask import Request

from exceptions import LogicalError
from responses.api import APIResponse, BadRequest, BizError


async def logical_exception_handler(request: Request, exc: LogicalError) -> APIResponse:
    if exc.code:
        return BizError(code=exc.code, message=exc.message)
    else:
        return BadRequest(message=exc.message)

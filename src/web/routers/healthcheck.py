import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.web.core.logging import rq_log_error, rq_log_info
from src.web.services.engine import health_check as engine_health_check

# import traceback


# from src.web.services.resource import health_check as resouces_health_check

router = APIRouter()

@router.get("/api/v1/health")
async def health_check(request: Request):
    t1 = time.time()
    errors = {}
    try:
        _ = engine_health_check()
    except Exception as e:
        # print(traceback.format_exc())
        errors["engine"] = str(e)
        rq_log_error(request, f'Engine health check failed: {e}')

    # try:
    #     _ = resouces_health_check()
    # except Exception as e:
    #     # print(traceback.format_exc())
    #     errors["resources"] = str(e)
    #     rq_log_error(request, f'Resouces health check failed: {e}')
    t2 = time.time()

    if errors:
        return JSONResponse({"message":"Health check failed", "errors": errors}, status_code=500)
    rq_log_info(request, f'Health check succeeded, Time = {(t2 - t1):.06f} seconds')
    return JSONResponse({"status": "healthy"}, status_code=200)

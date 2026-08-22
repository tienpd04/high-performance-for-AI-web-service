import time
# from src.web.services.engine import inference
# import traceback

import numpy as np
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.web.core.logging import rq_log_error, rq_log_info
from src.web.services.face_recog import face_recog

router = APIRouter()

@router.get("/api/v1/inference")
async def inference_api(request: Request):
    input_tensor = np.full((1024, 1024, 3), 255, dtype=np.uint8)
    t1 = time.time()
    try:
        response = face_recog(input_tensor)
    except Exception as e:
        # traceback.print_exc()
        rq_log_error(request, f'inference failed: {e}')
        return JSONResponse(status_code=500, content={'success': False, 'message': f'Inference failed: {e}'})
    t2 = time.time()
    # array = response[0]
    # print(f"Output array =\n{array}")
    # print(response)
    rq_log_info(request, f'Inference successfully. Time = {(t2 - t1):.06f} seconds')
    return JSONResponse( {'success': True, 'message': 'inference successfully'})
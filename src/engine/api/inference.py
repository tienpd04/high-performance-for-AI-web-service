
import os
import pickle
import secrets
from multiprocessing.shared_memory import SharedMemory
from typing import cast

import numpy as np
from numpy.typing import NDArray

from src.config.engine import STORAGE_DIR, ShmTensorSchema

from ..core.engine import Engine, InvalidModelName
from ..core.shm import get_shm
from ..utils.logging import logger
from .common import (ASCIIJsonResponse, JSONResponse, PlainTextResponse, Response, Request,
                     SocketApplicaltion)
# import time

try:
    STORAGE_DIR.encode('ascii')
except Exception:
    FileModeResponse = JSONResponse
else:
    FileModeResponse = ASCIIJsonResponse


def _load_shm_input_tensor(tensor_info: dict) -> tuple[NDArray, SharedMemory]:

    tensor_schema = ShmTensorSchema(**tensor_info)
    shm = get_shm(tensor_schema.shm)
    tensor = np.ndarray(shape=tensor_schema.shape, dtype=tensor_schema.dtype, buffer=shm.buf)
    return tensor, shm

def _bind_ouputs(outputs: list[NDArray], shm: SharedMemory) -> list[ShmTensorSchema]:

    shm_buff = shm.buf
    buf_from = 0
    tensor_schemas: list[ShmTensorSchema] = []
    for tensor in outputs:
        buf = shm_buff if buf_from == 0 else shm_buff[buf_from]
        array = np.ndarray(shape=tensor.shape, dtype=tensor.dtype, buffer=buf)
        array[:] = tensor[:]
        buf_from += array.nbytes
        schema = ShmTensorSchema(shape=tensor.shape, dtype=tensor.dtype.name, shm=shm.name, buf_from=buf_from)
        tensor_schemas.append(schema)

    return tensor_schemas




def inference(req: Request) -> Response:
    '''
    Health Check API

    Return:
    JsonResponse if success
    PlainTextResponse with message if have error
    '''
    try:
        data = req.json()
        assert isinstance(data, dict), ""
    except Exception:
        return PlainTextResponse("Required content as a dict type", 422)

    model_name = data.get('model_name')
    mode = data.get('mode')
    if mode not in ['shm', 'file']:
        return PlainTextResponse(f"Invalid mode: '{mode}'")

    # t1 = time.time()
    try:
        if mode == 'shm':
            tensor_info = data.get('input_tensor')
            input_tensor, shm = _load_shm_input_tensor(tensor_info)

        else:
            filepath = data.get('filepath')
            input_tensor = np.load(filepath)
    except Exception as e:
        return PlainTextResponse(f"Could not load input tensor: {str(e)}", 422)

    # logger.info("Load input time: %0.6f", time.time() - t1)


    engine = cast(Engine, getattr(cast(SocketApplicaltion, req.app).state, "engine"))
    try:
        outputs = engine.inference(model_name=model_name, input_tensor=input_tensor)
    except InvalidModelName:
        logger.warning("Invalid model name: %s", model_name)
        return PlainTextResponse(f"Invalid model name: {model_name}", 422)
    except Exception as e:
        logger.error("Error during inference: %s", str(e))
        return PlainTextResponse(f"Error while during inference: {e}", 500)

    output_mode = mode
    if output_mode == 'shm':
        total_size = sum(o.nbytes for o in outputs)
        if total_size > shm.size:
            logger.warning("Shm not enough size to write the output, expected: %d, shm size: %d. Try to write output with 'file' mode", total_size, shm.size)
            output_mode = 'file'

    if output_mode == 'shm':
        try:
            output_schemas = _bind_ouputs(outputs=outputs, shm=shm)
        except Exception as e:
            logger.error("Could not bind output to shm: shm name '%s', shm size %d. Exception: %s", shm.name, shm.size, str(e))
            return PlainTextResponse("Could not bind output to shm: shm name '{}', shm size {}. Exception: {}".format(shm.name, shm.size, str(e)), 500)

        content = {'mode': output_mode, 'outputs': [s.origin_dict() for s in output_schemas]}
        # Switch to JsonResponse if the SHM name contains Unicode characters (non-ASCII).
        return ASCIIJsonResponse(content)
    else:
        filepath = os.path.join(STORAGE_DIR, secrets.token_hex(16) + '.pkl')
        with open(filepath, 'wb') as f:
            pickle.dump(outputs, f)
        content =  {'mode': output_mode, 'outputs': {'filepath': filepath}}
        return FileModeResponse(content)



__all__ = [
    "inference",
]
import os
import pickle
import secrets
import time
from typing import cast

import numpy as np
from numpy.typing import NDArray

from src.config.engine import ENGINE_SOCKET_ADDRESS as ADDRESS
from src.config.engine import ENGINE_SOCKET_FAMILY as SOCKET_FAMILY
from src.config.engine import ENGINE_SOCKET_KIND as SOCKET_KIND
from src.config.engine import STORAGE_DIR
from src.config.engine import EngineSocketAPI as SocketAPI
from src.config.engine import ShmTensorSchema
from src.libs.socket_protocol.client.exceptions import (RequestException,
                                                        StatusCodeError)
from src.libs.socket_protocol.client.requests import request
from src.web.core.logging import logger

from .resources import acquire, get_shm, release


def health_check(raise_exp=True, timeout=10) -> bool:
    try:
        res = request(ADDRESS, SocketAPI.HEALTH_CHECK,
                    address_family=SOCKET_FAMILY, socket_kind=SOCKET_KIND, timeout=timeout)
        res.raise_for_status()
    except Exception:
        if raise_exp:
            raise
        return False

    return True


def _load_ouputs_from_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            output_tensors = pickle.load(f)
        return output_tensors

    finally:
        try:
            os.remove(filepath)
        except Exception:
            pass

def _load_outputs(response_dict: dict) -> list[NDArray]:

    mode = response_dict.get("mode")
    outputs: list | dict = response_dict.get("outputs")

    if mode == "shm":
        # shm_size = tensor_info.get("shm_size")
        list_outputs: list[NDArray] = []
        for tensor_info in outputs:
            tensor_schema = ShmTensorSchema(**tensor_info)
            shm = get_shm(tensor_schema.shm)
            buf = shm.buf[tensor_schema.buf_from:]
            output_tensor = np.ndarray(
                shape=tensor_schema.shape, dtype=tensor_schema.dtype, buffer=buf).copy()
            list_outputs.append(output_tensor)

        return list_outputs

    elif mode == "file":
        filepath = outputs.get('filepath')
        return _load_ouputs_from_file(filepath)




def _genegate_filestem(size=16):
    return secrets.token_hex(size)


def _inference_from_file(model_name: str, tensor_file_path: str, timeout=10) -> list[NDArray]:
    content = {'model_name': model_name, "mode": "file", "filepath": tensor_file_path}
    try:
        res = request(ADDRESS, SocketAPI.INFERENCE, data=content,
                    address_family=SOCKET_FAMILY, socket_kind=SOCKET_KIND, timeout=timeout)
        res.raise_for_status()
        response_dict = res.json()
        assert isinstance(response_dict, dict), "Content return must be a dict"


    except StatusCodeError as e:
        try:
            msg = res.text
        except Exception:
            msg = str(e)
        raise RequestException(f"Request failed with status code {res.status_code}: {msg}") from e
    except Exception as e:
        logger.error(
            "Failed to request inference from engine with exception: %s", str(e))
        # logger.error(traceback.format_exc())
        raise

    # Inferece from file always return 'file' mode
    filepath = cast(dict, response_dict.get('outputs')).get("filepath")
    outputs = _load_ouputs_from_file(filepath)

    return outputs


def inference(model_name: str, input_tensor: NDArray, timeout=None) -> list[NDArray]:

    shms = acquire([input_tensor.nbytes])

    if not shms:
        logger.warning("Failed to acquire shared memory with size %d, try request to engine with 'file' mode", input_tensor.nbytes)
        file_path = os.path.join(STORAGE_DIR, _genegate_filestem() + ".npy")
        np.save(file_path, input_tensor)
        try:
            return _inference_from_file(model_name, file_path, timeout=timeout)
        finally:
            try:
                os.remove(file_path)
            except Exception:
                pass

    else:
        shm = shms[0]
        try:
            array = np.ndarray(shape=input_tensor.shape,
                            dtype=input_tensor.dtype, buffer=shm.buf)
            array[:] = input_tensor[:]
            tensor_content = ShmTensorSchema(shape=[int(x) for x in input_tensor.shape], dtype=input_tensor.dtype.name, shm=shm.name).to_dict()
            content = {'model_name': model_name, 'input_tensor': tensor_content, 'mode': 'shm'}

            res = request(ADDRESS, SocketAPI.INFERENCE, data=content,
                        address_family=SOCKET_FAMILY, socket_kind=SOCKET_KIND, timeout=timeout)
            res.raise_for_status()
            response_dict = res.json()
            assert isinstance(
                response_dict, dict), "Content return must be a dict"
            outputs = _load_outputs(response_dict)
            return outputs
        finally:
            release(shms)



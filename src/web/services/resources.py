from multiprocessing.shared_memory import SharedMemory

from src import resourcesmng

_shm_cache: dict[str, SharedMemory] = {}


def get_shm(name: str) -> SharedMemory:
    shm = _shm_cache.get(name)
    if shm is None:
        shm = SharedMemory(name)
        _shm_cache[name] = shm

    return shm



def acquire(sizes: list[int]) -> list[SharedMemory] | None:
    ret =  resourcesmng.acquire(sizes=sizes)
    if ret is None:
        return ret
    return [get_shm(x) for (x, _) in ret]



def release(resouces: list[SharedMemory]) -> bool:
    return resourcesmng.release([shm.name for shm in resouces])


__all__ = [
    "get_shm",
    "acquire",
    "release"
]

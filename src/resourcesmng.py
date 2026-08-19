import time
from multiprocessing import Lock
from types import MappingProxyType


class _ResourcesManager:
    _resources: MappingProxyType[str, int]
    _usage_time_limit: int | float
    _last_use_times: dict[str, float]
    _maxsize: int

    def __init__(self, resources: dict[str, int], usage_time_limit=180):
        self._resources = MappingProxyType(resources)
        self._usage_time_limit = usage_time_limit
        self._last_use_times = {}
        self._maxsize = max(self._resources.values())

    @property
    def usage_time_limit(self):
        return self._last_use_times

    def acquire(self, req_sizes: list[int]) -> list[tuple[str, int]] | None:
        if not req_sizes or len(req_sizes) > len(self._resources):
            return None
        sorted_req_sizes = sorted(req_sizes)
        if sorted_req_sizes[-1] > self._maxsize:
            return None

        sorted_resources = []

        avaiable = [(k, v) for k, v in self._resources.items(
        ) if k not in self._last_use_times and sorted_req_sizes[0] <= v]
        avaiable.sort(key=lambda k: k[1], reverse=True)

        now = time.time()
        miss: list[int] = []
        for size in sorted_req_sizes:
            found = False
            while avaiable:
                src, src_size = avaiable.pop()
                if src_size < size:
                    continue
                sorted_resources.append((src, src_size))
                found = True
                break
            if not found:
                miss.append(size)

        if miss:
            from_overdue = []
            outofdate = self.overdue(now)
            names = [k[0] for k in outofdate]
            names.sort(key=self._resources.get, reverse=True)
            for size in miss:
                found = False
                while names:
                    src = names.pop()
                    src_size = self._resources[src]
                    if src_size < size:
                        continue

                    from_overdue.append((src, src_size))
                    found = True
                    break
                if not found:
                    return None

            sorted_resources.extend(from_overdue)
            sorted_resources.sort(key=lambda k: k[1])

        if len(sorted_resources) == len(req_sizes):

            for src, _ in sorted_resources:
                self._last_use_times[src] = now

            sorted_idxs = sorted(range(len(req_sizes)),
                                 key=lambda k: req_sizes[k])
            ret = [None] * len(req_sizes)
            for i, idx in enumerate(sorted_idxs):
                ret[idx] = sorted_resources[i]
            return ret

        return None

    def release(self, resources: list[str]) -> bool:
        ret = True
        for src in set(resources):
            ret = ret and (self._last_use_times.pop(src, None) is not None)

        return ret

    def overdue(self, now: float = None) -> list[tuple[str, float]]:
        if now is None:
            now = time.time()
        ret = []
        for src, last_time in self._last_use_times.items():
            if now - last_time > self._usage_time_limit:
                ret.append((src, now - last_time))
        return ret


class _OneSizeResourcesManager(_ResourcesManager):

    def __init__(self, resources: set[str], size: int, usage_time_limit=180):
        _ResourcesManager.__init__(self, {k: size for k in resources}, usage_time_limit)


    def acquire(self, req_sizes: list[int]) -> list[tuple[str, int]] | None:
        if not req_sizes or len(req_sizes) > len(self._resources):
            return None

        src_size = self._maxsize
        if max(req_sizes) > src_size:
            return None

        now = time.time()
        avaiable = set(self._resources) - set(self._last_use_times)
        ret_names = []

        if len(avaiable) >= len(req_sizes):
            ret_names = list(avaiable)[:len(req_sizes)]

        else:
            outofdate = self.overdue(now)
            if len(outofdate) + len(avaiable) < len(req_sizes):
                return None

            ret_names = list(
                avaiable) + [k[0] for k in outofdate][:len(req_sizes)-len(avaiable)]

        ret = []
        for k in ret_names:
            self._last_use_times[k] = now
            ret.append((k, src_size))

        return ret


_lock = Lock()

_resources_mng = None

def initialize(resouces: dict[str, int], usage_time_limit=180):
    with _lock:
        global _resources_mng
        assert _resources_mng is None, "Resources Manage initialize called too many time"
        set_of_sizes = set(resouces.values())
        if len(set_of_sizes) == 1:
            _resources_mng = _OneSizeResourcesManager(set(resouces.keys()), size=set_of_sizes.pop(), usage_time_limit=usage_time_limit)
        else:
            _resources_mng = _ResourcesManager(resources=resouces, usage_time_limit=usage_time_limit)

def acquire(sizes: list[int]):
    with _lock:
        return _resources_mng.acquire(sizes)

def release(names: list[str]):
    with _lock:
        return _resources_mng.release(names)

def overdue(now: float = None)-> list[tuple[str, float]]:
    with _lock:
        return _resources_mng.overdue(now=now)

def usage_time_limit():
    with _lock:
        return _resources_mng.usage_time_limit

__all__ = [
    'initialize',
    'acquire',
    'release',
    'overdue',
    'usage_time_limit',
]
import contextlib
import copy
import dataclasses as dc
import json
import time
import typing as t
from functools import cached_property
from threading import Lock

from superduperdb.base.config_dicts import combine

Address = t.Tuple[str, ...]
StrDict = t.Dict[str, t.Any]

# https://github.com/SuperDuperDB/superduperdb/discussions/644


class Output:
    """Outputs to the actual logger"""

    def log(self, record: StrDict):
        print(json.dumps(record))


class Base:
    __address__: t.ClassVar[Address]

    def __init__(self, output: Output):
        for k, v in self._entries().items():
            v._on_add(output, self, k)

    def __init_subclass__(cls, **ka):
        Base._SUBCLASSES.append(cls)

    @classmethod
    def _entries(cls) -> t.Dict[str, 'Entry']:
        it = vars(cls).items()
        return {k: v for k, v in it if not k.startswith('_') and isinstance(v, Entry)}

    @staticmethod
    def _test_subclasses() -> None:
        d: t.Dict[Address, t.List[t.Type]] = {}
        for sub in Base._SUBCLASSES:
            d.setdefault(sub._address__, []).append(sub)
        if dupes := {k: v for k, v in d.items() if len(v) > 1}:
            raise ValueError(f'Duplicate log address: {dupes}')

    @staticmethod
    def log_list() -> StrDict:
        Base._test_subclasses()
        return combine(s._log_list() for s in Base._SUBCLASSES)

    @classmethod
    def _log_list(cls) -> StrDict:
        return {}

    _SUBCLASSES: t.ClassVar[t.List[t.Type]] = []


class Entry:
    output: Output = Output()
    initial_value: t.Any = 0
    address: Address = ()

    def _log(self):
        self.output.log(self.record())

    def _on_add(self, output: Output, log: Base, key: str):
        assert not self.address, 'Entries can only be added once'
        self.address = *log.__address__, key
        self.output = output

    @cached_property
    def record(self) -> StrDict:
        assert self.address
        self._parent = {}
        r = copy.deepcopy(self.initial_value)
        for k in reversed(self.address):
            r = {k: r}
            self._parent = self._parent or r
        return r

    _parent: dict

    @cached_property
    def _key(self) -> str:
        return self.address[-1]

    def _set(self, value: t.Any) -> None:
        self._parent[self._key] = value

    def _get(self) -> t.Any:
        return self._parent[self._key]

    @cached_property
    def lock(self) -> Lock:
        return Lock()


class Counter(Entry):
    def count(self, delta: int = 1):
        with self.lock:
            self._set(self._get() + 1)


class Elapsed(Entry):
    @contextlib.contextmanager
    def time(self):
        start = time.time()
        try:
            yield
        finally:
            with self.lock:
                self._set(self._get() + time.time() - start)


class Success(Entry):
    @dc.dataclass
    class Record:
        # These three names need to be added to the log list
        count: int = 0
        succeed: int = 0
        fail: int = 0

    initial_value = Record()

    @contextlib.contextmanager
    def run(self):
        with self.lock:
            self._get().count += 1
        try:
            succeed = False
            yield
            succeed = True
        finally:
            with self.lock:
                if succeed:
                    self._get().succeed += 1
                else:
                    self._get().fail += 1


"""
https://github.com/SuperDuperDB/superduperdb/discussions/644

TODOs:
* Contexts for loguru or `logging`
* The three Generic entries Simple, Enumerate, Data
*
"""

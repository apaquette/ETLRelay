
from typing import BinaryIO, Protocol, runtime_checkable


class FileSystemError(Exception):
    ...

@runtime_checkable
class FileSystem(Protocol):
    def open_read(self, path: str) -> BinaryIO:
        ...
    def open_write(self, path: str) -> BinaryIO:
        ...
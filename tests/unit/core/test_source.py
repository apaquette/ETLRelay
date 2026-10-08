
from collections.abc import Iterable

from flowforge.core.batch import Batch
from flowforge.core.source import Source


class TestSource:
    def test_source_satisfies_protocol(self) -> None:
        class DummySource(Source):
            def read(self) -> Iterable[Batch]:
                return [Batch(
                            table=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ]
        )]

        source = DummySource()
        assert isinstance(source, Source)
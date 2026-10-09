
from collections.abc import Iterable

from etlrelay.core.batch import Batch
from etlrelay.core.sink import Sink


class TestSink:
    def test_sink_satisfies_protocol(self) -> None:
        class DummySink(Sink):
            def write(self, batches: Iterable[Batch]) -> None:
                pass

        sink = DummySink()
        assert isinstance(sink, Sink)
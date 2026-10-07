

from flowforge.core.batch import Batch
from flowforge.core.sink import Sink


class TestSink:
    def test_sink_satisfies_protocol(self) -> None:
        class DummySink(Sink):
            def write(self, batch: Batch) -> None:
                pass

        sink = DummySink()
        assert isinstance(sink, Sink)
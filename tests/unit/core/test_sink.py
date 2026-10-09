from collections.abc import Iterable

from etlrelay.core import Batch, Sink


class TestSink:
    def test_sink_satisfies_protocol(self) -> None:
        class DummySink(Sink):
            def write(self, batches: Iterable[Batch]) -> None:
                pass

        sink = DummySink()
        assert isinstance(sink, Sink)

from etlrelay.core.batch import Batch
from etlrelay.core.processor import Processor


class IdentitfyProcessor:
    def process(self, batch: Batch) -> Batch:
        # Simply return the batch as is
        return batch

class TestProcessor:
    def test_processor_accepts_batch_and_returns_batch(self) -> None:
        # Create a sample batch
        batch = Batch(
            table=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ]
        )

        # Create an instance of the processor
        processor: Processor = IdentitfyProcessor()

        # Process the batch
        processed_batch = processor.process(batch)

        # Assert that the processed batch is the same as the input batch
        assert processed_batch.table == batch.table
        assert isinstance(processed_batch, Batch)
        assert isinstance(processor, Processor) 
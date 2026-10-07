import pyarrow as pa


class Batch:
    def __init__(self, table: pa.Table) -> None:
        self._table = table
    
    @property
    def table(self) -> pa.Table:
        return self._table
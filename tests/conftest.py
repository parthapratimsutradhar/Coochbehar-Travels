import json
import sqlite3

from sqlalchemy import ARRAY
from sqlalchemy.dialects.postgresql import JSONB, ARRAY as PG_ARRAY
from sqlalchemy.ext.compiler import compiles

compiles(JSONB, "sqlite")(lambda type_, compiler, **kw: "JSON")
compiles(ARRAY, "sqlite")(lambda type_, compiler, **kw: "JSON")
compiles(PG_ARRAY, "sqlite")(lambda type_, compiler, **kw: "JSON")

sqlite3.register_adapter(list, lambda l: json.dumps([str(x) for x in l]))

orig_result_processor = PG_ARRAY.result_processor


def sqlite_array_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    itemproc = self.item_type.result_processor(dialect, coltype)
                    if itemproc:
                        return [itemproc(x) for x in parsed]
                    return parsed
                except Exception:
                    pass
            return value
        return process
    return orig_result_processor(self, dialect, coltype)


PG_ARRAY.result_processor = sqlite_array_result_processor

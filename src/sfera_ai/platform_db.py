from collections.abc import Sequence

from sqlalchemy import Engine, MetaData
from sqlalchemy.ext.automap import AutomapBase, automap_base


def reflect_platform_tables(engine: Engine, *, tables: Sequence[str]) -> AutomapBase:
    metadata = MetaData()
    metadata.reflect(bind=engine, only=tables)
    base = automap_base(metadata=metadata)
    base.prepare()
    return base

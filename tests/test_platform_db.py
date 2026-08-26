from sqlalchemy import create_engine

from sfera_ai.platform_db import reflect_platform_tables

PLATFORM_TABLES = ("courses_application", "testchecks_answer")


def test_reflect_platform_tables_exposes_only_listed_tables():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_application (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE unrelated_table (id INTEGER PRIMARY KEY)")

    base = reflect_platform_tables(engine, tables=PLATFORM_TABLES)

    assert set(base.classes.keys()) == {"courses_application", "testchecks_answer"}

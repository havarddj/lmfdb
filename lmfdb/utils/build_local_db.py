import argparse
import os
import subprocess

from lmfdb.utils.config import ConfigWrapper
from lmfdb.lmfdb_database import LMFDBDatabase

# NB: using Configuration from 
from psycodict.database import PostgresDatabase
from psycodict.config import Configuration
from psycopg2.sql import SQL

# Tables that must be fully included for LMFDB to work
FULL_COPY_TABLES = [
    "meta_tables",
    "kwl_knowls",
    "userdb.users"
    "userdb.dbrecord"
]

# Default number of rows to copy from each table
DEFAULT_COPY_ROWS = 2000

def get_meta_table_schemas(db):
    """Get column names and types using psycodict author's method."""

    query = SQL("""
        SELECT column_name, udt_name::regtype 
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position
    """)
    return {table: get_table_schema(source_db, list(db._execute(query, [table]))
               for table in FULL_COPY_TABLES}


def create_table_from_schemas(target_conn, table_name, schema):
    """Create table on target database."""
    columns = [f"{col} {typ}" for col, typ in schema]
    create_stmt = f"CREATE TABLE {table_name} ({', '.join(columns)})"

    with target_conn.cursor() as cur:
        cur.execute(create_stmt)
    target_conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Build a local LMFDB development database with a row-limited subset of data."
    )
    parser.add_argument(
        "-r", "--rows", type=int, default=DEFAULT_COPY_ROWS,
        help=f"Max rows to copy per table (default: {DEFAULT_COPY_ROWS})"
    )
    parser.add_argument(
        "-t", "--tables", type=str, default=None,
        help="Comma-separated list of tables to copy (default: all).\nMeta/knowl tables are always included."
    )
    parser.add_argument(
        "-f", "--db-folder", default="lmfdb_local_db",
        help="Name of the local folder to write database into (default: lmfdb_local_db)."
        ""
    )
    parser.add_argument(
        "-n", "--db-name", default="lmfdb_local_db",
        help="Name of the local database (default: lmfdb_local_db)."
        ""
    )
    parser.add_argument(
        "-c", "--config-file", default="localhost",
        help="Host of the local database (default: localhost)"
    )
    
    args = parser.parse_args()
    data_folder = args.db_folder
    db_name = args.db_name

    # Step 1: fetch meta schemas
    from lmfdb import db
    get_meta_table_schemas(db)
    
    # Step 2: get data from tables (TODO: edit copy_to to take rows)
    # Step 3: initalize local DB with meta schemas

    # Connect to local database
    # TODO: needs to be LMFDB version
    local_config = Configuration(defaults={"config_file": "config_local.ini"},
                           writeargstofile=False, readargs=False)

    new_db = LMFDBDatabase(config = local_config)
    for (table_name, schema) in schemas.items():
        create_table_from_schemas(target_conn, table_name, schema)

    # Step 4: run reload all





    # local_db = PostgresDatabase(local_config)
    # data_folder = Path("lmfdb_local_db")

    print(schemas)
    # create_table_from_schema(target_conn, "meta_tables", schema)
        # print(db.tablenames)
        # db.copy_to(FULL_COPY_TABLES, data_folder)
        # for table in FULL_COPY_TABLES:
        #     print(list(db._execute(SQL("SELECT column_name, udt_name::regtype FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position"), [table])))


    
if __name__ == "__main__":
    main()

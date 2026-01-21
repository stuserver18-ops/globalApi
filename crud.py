# crud.py
from typing import Optional, List, Dict, Any, Tuple, cast
from db import get_connection, fetch_all, execute

# -------------------------------
# CRUD Helper Functions
# -------------------------------

def add(
    table: str,
    data: Dict[str, Any],
    app_name: Optional[str] = None
) -> int:
    """
    Insert a row into `table`.
    - data: dict of column:value
    - app_name: optional database name
    Returns: last inserted id
    """
    if not data:
        raise ValueError("Data dictionary cannot be empty")

    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    values = tuple(data.values())

    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    result = execute(query, values, app_name)
    if result is None:
        raise RuntimeError("Insert did not return an id")
    return int(result)


def update(
    table: str,
    data: Dict[str, Any],
    where: Optional[str] = None,
    params: Tuple = (),
    app_name: Optional[str] = None
) -> int:
    """
    Update rows in `table`.
    - data: dict of column:value to update
    - where: optional SQL WHERE clause (without 'WHERE')
    - params: tuple of values for WHERE placeholders
    - app_name: optional database name
    Returns: number of affected rows
    """
    if not data:
        raise ValueError("Data dictionary cannot be empty")

    set_clause = ", ".join([f"{col} = %s" for col in data.keys()])
    values = tuple(data.values())
    
    query = f"UPDATE {table} SET {set_clause}"
    if where:
        query += f" WHERE {where}"
        values += params

    conn = get_connection(app_name)
    cursor = conn.cursor()
    try:
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount
    finally:
        try:
            cursor.close()
        finally:
            conn.close()


def delete(
    table: str,
    where: Optional[str] = None,
    params: Tuple = (),
    app_name: Optional[str] = None
) -> int:
    """
    Delete rows from `table`.
    - where: optional SQL WHERE clause
    - params: tuple of values for WHERE placeholders
    - app_name: optional database name
    Returns: number of affected rows
    """
    query = f"DELETE FROM {table}"
    if where:
        query += f" WHERE {where}"

    conn = get_connection(app_name)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
    finally:
        try:
            cursor.close()
        finally:
            conn.close()


def get(
    table: str,
    columns: Optional[List[str]] = None,
    where: Optional[str] = None,
    params: Tuple = (),
    app_name: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch rows from `table`.
    - columns: list of columns to fetch (default: all)
    - where: optional SQL WHERE clause
    - params: tuple of values for WHERE placeholders
    - limit: optional limit of rows
    - app_name: optional database name
    Returns: list of dictionaries
    """
    cols = ", ".join(columns) if columns else "*"
    query = f"SELECT {cols} FROM {table}"
    if where:
        query += f" WHERE {where}"
    if limit:
        query += f" LIMIT {limit}"

    return cast(List[Dict[str, Any]], fetch_all(query, params, app_name))

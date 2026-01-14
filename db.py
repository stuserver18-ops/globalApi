import mysql.connector
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

HOST = os.getenv("DB_SERVER", "localhost")
USER = os.getenv("DB_USER", "root")
PASSWORD = os.getenv("DB_PASSWORD", "")


def get_connection(app_name: Optional[str] = None):
    """
    Create and return a MySQL connection.
    If `app_name` is provided it will be used as the database name;
    otherwise no `database` parameter is passed (uses server default).
    """
    connect_kwargs = {
        "host": HOST,
        "user": USER,
        "password": PASSWORD,
    }
    if app_name:
        connect_kwargs["database"] = app_name

    return mysql.connector.connect(**connect_kwargs)


def fetch_all(query, params=(), app_name: Optional[str] = None):
    conn = get_connection(app_name)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return rows
    finally:
        try:
            cursor.close()
        finally:
            conn.close()


def execute(query, params=(), app_name: Optional[str] = None):
    conn = get_connection(app_name)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        try:
            cursor.close()
        finally:
            conn.close()

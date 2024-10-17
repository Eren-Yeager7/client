"""
Originall designed for shop database :(
"""


import sqlite3
from typing import List, Optional, Dict, Any, Tuple

class Database:
    def __init__(self, db_file: str):
        """Initialise the sqlite3 db with a database file."""

        self.db_file = db_file
        self.connection: Optional[sqlite3.Connection] = None # equivalant to Union[X, None] or X | None
        self.cursor: Optional[sqlite3.Cursor] = None

    def open(self) -> None:
        """Open a connection to sqlite3 db"""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_file)
            self.cursor = self.connection.cursor()
        else:
            print("database connection is already open")

    def close(self) -> None:
        """Close the sqlite3 db connection"""
        if self.connection: # check if connection is valid
            self.commit() # comminut any pending transactions
            self.connection.close()

            # set variables to None to clear memory *safety*
            self.connection = None
            self.cursor = None
        else:
            print("database connection is null")

    def insert(self, table: str, data: Dict[str, Any]) -> None:
        """Insert a row into specified table

        Args:
            table (str): Name of the table to insert data into
            data (Dict[str, Any]): Dictionary of colum-value pairs to insert
        """
        sql: str = f"INSERT INTO {table} ({', '.join(data.keys())}) VALUES ({', '.join(['?'] * len(data))})"
        try:
            self.cursor.execute(sql, tuple(data.values()))
            self.commit()
            print(f"Inserted {data} into {table}")
        except Exception as e:
            print(f"Error Failed to insert into {table}: {e}")
            raise

    def query(self, sql_query: str, params: Optional[Tuple[Any]] = None) -> List[Tuple]:
        """_summary_

        Args:
            sql_query (str): query to execute
            params (Optional[Tuple[Any]], optional): Optional paramters for the query. Defaults to None.

        Returns:
            List[Tuple]: _description_
        """
        if params is None:
            params = () 
        
        self.cursor.execute(sql_query, params)
        rows = self.cursor.fetchall()
        print(f"query: {sql_query} | Params: {params} => Rows returned: {len(rows)}")
        return rows
    
    def search(self, table: str, search_query: Optional[Dict[str, Any]] = None) -> List[Tuple]:
        """search db rowsin specified table that match the given criteria

        Args:
            table (str):  Name of the table to search
            search_query (Dict[str, Any]): Dictionary of column-value pairs to match

        Returns:
            List[Tuple]: a list of tuples representing matching rows
        """
        sql: str = f"SELECT * FROM {table}"
        conditions: List[str] = []

        if search_query:
            conditions.append(" AND ".join([f"{col} = ?" for col in search_query.keys()]))

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        return self.query(sql, tuple(search_query.values()) if search_query else ())
    
    def delete(self, table: str, search_query: Dict[str, Any]) -> None:
        """delete the rows from specified table

        Args:
            table (str): Name of the table to delete from
            search_query (Dict[str, Any]): Dictionary of column-value pairs to match
        """
        sql: str = f"DELETE FROM {table} WHERE {' AND '.join([f"{col} = ?" for col in search_query.keys()])}"
        self.cursor.execute(sql, tuple(search_query.keys()))
        print("Deleted rows from {table} where {search_query}")

    def update(self, table: str, update_data: Dict[str, Any], search_query: Dict[str, Any]) -> None:
        """_summary_

        Args:
            table (str): _description_
            update_data (Dict[str, Any]): _description_
            search_query (Dict[str, Any]): _description_
        """
        sql: str = f"UPDATE {table} SET {', '.join([f"{col} = ?" for col in update_data.keys()])} WHERE {' AND '.join([f"{col} = ?" for col in search_query.keys()])}"
        self.cursor.execute(sql, tuple(update_data.values()) + tuple(search_query.values()))
        print(f"Updated {table} set {update_data} where {search_query}")
    
    def commit(self) -> None:
        """commit any current transactions"""
        if self.connection:
            self.connection.commit()
        else:
            print("No active connection to commit")

    """
    These magic methods allows us to implement object which can be used with the "with" statement
    This is just simply a try and finally block

    VAR = EXPR
    VAR.__enter__()
    try:
        BLOCK
    finally:
        VAR.__exit__()

    which translates to

    with VAR = EXPR:
        BLOCK

    Explanation: https://peps.python.org/pep-0343/
    """
    def __enter__(self) -> "Database":
        """enter runtime context related to the object"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the runtime context related to the object"""
        self.close()        

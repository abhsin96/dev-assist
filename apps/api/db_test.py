"""PostgreSQL database connection test script.

This script connects to the PostgreSQL database and retrieves the database version.
It uses environment variables for secure credential management.
"""

import os
import sys
from typing import Optional

import psycopg2
from psycopg2 import Error
from dotenv import load_dotenv


def get_database_url() -> str:
    """Get database URL from environment variables.
    
    Returns:
        str: Database connection URL
        
    Raises:
        ValueError: If DATABASE_URL is not set
    """
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Please check your .env file."
        )
    
    return database_url


def test_database_connection(connection_url: str) -> Optional[str]:
    """Test database connection and retrieve PostgreSQL version.
    
    Args:
        connection_url: PostgreSQL connection URL
        
    Returns:
        Optional[str]: PostgreSQL version string if successful, None otherwise
    """
    conn = None
    cur = None
    
    try:
        # Establish database connection
        print("Connecting to PostgreSQL database...")
        conn = psycopg2.connect(connection_url)
        
        # Create cursor
        cur = conn.cursor()
        
        # Execute version query
        query_sql = "SELECT VERSION()"
        cur.execute(query_sql)
        
        # Fetch and return version
        version = cur.fetchone()[0]
        print("✓ Successfully connected to database!")
        return version
        
    except Error as e:
        print(f"✗ Error connecting to PostgreSQL database: {e}", file=sys.stderr)
        return None
        
    finally:
        # Clean up resources
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("Database connection closed.")


def main() -> None:
    """Main function to test database connection."""
    try:
        # Get database URL from environment
        database_url = get_database_url()
        
        # Test connection and get version
        version = test_database_connection(database_url)
        
        if version:
            print(f"\nPostgreSQL Version:\n{version}")
            sys.exit(0)
        else:
            print("\nFailed to retrieve database version.", file=sys.stderr)
            sys.exit(1)
            
    except ValueError as e:
        print(f"✗ Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

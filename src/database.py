"""
Database connection and session management.
Handles MySQL connection using SQLAlchemy.
"""

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self):
        """Initialize database connection parameters from environment variables."""
        self.host = os.getenv("DB_HOST")
        self.user = os.getenv("DB_USER")
        self.password = quote_plus(os.getenv("DB_PASSWORD", ""))
        self.database = os.getenv("DB_NAME")
        self.port = os.getenv("DB_PORT", "3306")

        # Validate required environment variables
        if not all([self.host, self.user, self.database]):
            raise ValueError(
                "Missing required database configuration. "
                "Please check your .env file and ensure DB_HOST, DB_USER, and DB_NAME are set."
            )

        # Create database URL
        self.database_url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

        # Create engine and session
        self.engine = create_engine(self.database_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_session(self):
        """Return the database session."""
        return self.session

    def get_engine(self):
        """Return the database engine."""
        return self.engine

    def close(self):
        """Close the database session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()


def get_db_connection():
    """
    Convenience function to get database connection.
    Returns a DatabaseManager instance.
    """
    return DatabaseManager()

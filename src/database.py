"""
Database connection and session management.
Handles MySQL connection using SQLAlchemy.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

# Load environment variables - handle PyInstaller bundled app
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    application_path = Path(sys.executable).parent
else:
    # Running as script
    application_path = Path(__file__).parent.parent

# Try to load .env from multiple locations
env_path = application_path / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✅ .env 파일 로드: {env_path}")
else:
    # Fallback to current directory
    load_dotenv()
    print(f"⚠️  .env 파일을 찾을 수 없음, 환경 변수 사용 시도")


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self):
        """Initialize database connection parameters from environment variables."""
        self.host = os.getenv("DB_HOST")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD", "")
        self.database = os.getenv("DB_NAME")
        self.port = int(os.getenv("DB_PORT", "3306"))

        # Debug: Print connection info (without password)
        print(f"🔌 DB 연결 시도: {self.user}@{self.host}:{self.port}/{self.database}")

        # Validate required environment variables
        if not all([self.host, self.user, self.database]):
            raise ValueError(
                "Missing required database configuration. "
                "Please check your .env file and ensure DB_HOST, DB_USER, and DB_NAME are set."
            )

        # Create database URL using URL.create() - automatically handles special characters
        database_url = URL.create(
            drivername="mysql+pymysql",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

        # Create engine and session
        self.engine = create_engine(database_url)
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

    def insert_sku_master(self, sku_record):
        """
        Insert new SKU_master record.

        Args:
            sku_record: Dict with SKU_master fields

        Returns:
            bool: True if successful, False otherwise
        """
        from models import SKU_master

        try:
            # Create new SKU_master instance
            new_sku = SKU_master(**sku_record)

            # Add and commit
            self.session.add(new_sku)
            self.session.commit()

            print(f"✅ SKU_master 추가 성공: ID_master={sku_record.get('ID_master')}")
            return True

        except Exception as e:
            print(f"❌ SKU_master 삽입 실패: {e}")
            self.session.rollback()
            return False

    def get_all_master_ids(self):
        """
        Get all existing ID_master values.

        Returns:
            set: Set of all ID_master values
        """
        from models import SKU_master

        try:
            results = self.session.query(SKU_master.ID_master).all()
            return {str(row[0]) for row in results}
        except Exception as e:
            print(f"❌ ID_master 조회 실패: {e}")
            return set()

    def get_sku_by_master_id(self, master_id):
        """
        Get SKU_master record by ID_master.

        Args:
            master_id: ID_master value

        Returns:
            dict or None: SKU record as dictionary
        """
        from models import SKU_master

        try:
            sku = self.session.query(SKU_master).filter(
                SKU_master.ID_master == master_id
            ).first()

            if sku:
                return sku.to_dict()
            return None

        except Exception as e:
            print(f"❌ SKU_master 조회 실패: {e}")
            return None


def get_db_connection():
    """
    Convenience function to get database connection.
    Returns a DatabaseManager instance.
    """
    return DatabaseManager()

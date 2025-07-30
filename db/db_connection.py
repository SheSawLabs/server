"""
Database Connection Management

PostgreSQL 데이터베이스 연결 및 쿼리 실행을 관리하는 모듈
"""

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Union
import logging
import sys
import os

# config 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """PostgreSQL 데이터베이스 연결 관리 클래스"""
    
    def __init__(self, min_connections: int = 1, max_connections: int = 10):
        """
        데이터베이스 매니저 초기화
        
        Args:
            min_connections: 최소 연결 수
            max_connections: 최대 연결 수
        """
        self.connection_pool: Optional[SimpleConnectionPool] = None
        self.min_connections = min_connections
        self.max_connections = max_connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """연결 풀 초기화"""
        try:
            self.connection_pool = SimpleConnectionPool(
                self.min_connections,
                self.max_connections,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        연결 풀에서 연결을 가져오는 컨텍스트 매니저
        
        Usage:
            with db_manager.get_connection() as conn:
                # 연결 사용
                pass
        """
        connection = None
        try:
            if self.connection_pool is None:
                raise Exception("Connection pool is not initialized")
            
            connection = self.connection_pool.getconn()
            yield connection
        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            logger.error(f"Database connection error: {e}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        finally:
            if connection and self.connection_pool:
                try:
                    self.connection_pool.putconn(connection)
                except:
                    pass
    
    def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 as test_value")
                    result = cursor.fetchone()
                    # RealDictCursor를 사용하므로 딕셔너리 형태로 반환됨
                    return result['test_value'] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        SELECT 쿼리 실행
        
        Args:
            query: SQL 쿼리
            params: 쿼리 파라미터
            
        Returns:
            쿼리 결과 리스트
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_non_query(self, query: str, params: Optional[tuple] = None) -> int:
        """
        INSERT/UPDATE/DELETE 쿼리 실행
        
        Args:
            query: SQL 쿼리
            params: 쿼리 파라미터
            
        Returns:
            영향받은 행 수
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"Non-query execution failed: {e}")
            raise
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        대량 INSERT 실행
        
        Args:
            query: SQL 쿼리
            params_list: 파라미터 리스트
            
        Returns:
            영향받은 행 수
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            raise
    
    def create_table_if_not_exists(self, table_name: str, schema_sql: str) -> bool:
        """
        테이블이 존재하지 않으면 생성
        
        Args:
            table_name: 테이블 이름
            schema_sql: CREATE TABLE SQL
            
        Returns:
            생성 성공 여부
        """
        try:
            # 테이블 존재 여부 확인
            check_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """
            
            result = self.execute_query(check_query, (table_name,))
            table_exists = result[0]['exists']
            
            if not table_exists:
                self.execute_non_query(schema_sql)
                logger.info(f"Table '{table_name}' created successfully")
                return True
            else:
                logger.info(f"Table '{table_name}' already exists")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create table '{table_name}': {e}")
            raise
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """테이블 정보 조회"""
        query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """
        return self.execute_query(query, (table_name,))
    
    def close_all_connections(self):
        """모든 연결 종료"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("All database connections closed")


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """데이터베이스 매니저 인스턴스 반환"""
    return db_manager


def init_database():
    """데이터베이스 초기화 (테이블 생성 등)"""
    try:
        # schema.sql 파일 읽기 및 실행
        schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if os.path.exists(schema_file):
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # 각 CREATE TABLE 문을 분리하여 실행
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement.upper().startswith('CREATE TABLE'):
                    db_manager.execute_non_query(statement)
                    
            logger.info("Database schema initialized successfully")
        else:
            logger.warning("schema.sql file not found")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def main():
    """데이터베이스 연결 테스트"""
    print("=== 데이터베이스 연결 테스트 ===\n")
    
    # 연결 테스트
    print("1. 연결 테스트:")
    if db_manager.test_connection():
        print("   ✅ 데이터베이스 연결 성공!")
    else:
        print("   ❌ 데이터베이스 연결 실패!")
        return
    
    # 데이터베이스 정보 조회
    print("\n2. 데이터베이스 정보:")
    try:
        version_result = db_manager.execute_query("SELECT version();")
        print(f"   PostgreSQL 버전: {version_result[0]['version']}")
        
        db_result = db_manager.execute_query("SELECT current_database();")
        print(f"   현재 데이터베이스: {db_result[0]['current_database']}")
        
        user_result = db_manager.execute_query("SELECT current_user;")
        print(f"   현재 사용자: {user_result[0]['current_user']}")
        
    except Exception as e:
        print(f"   정보 조회 중 오류: {e}")
    
    # 테이블 목록 조회
    print("\n3. 테이블 목록:")
    try:
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """
        tables = db_manager.execute_query(tables_query)
        
        if tables:
            for table in tables:
                print(f"   - {table['table_name']}")
        else:
            print("   테이블이 없습니다.")
            
    except Exception as e:
        print(f"   테이블 조회 중 오류: {e}")
    
    print("\n연결 풀 정보:")
    if db_manager.connection_pool:
        print(f"   최소 연결: {db_manager.min_connections}")
        print(f"   최대 연결: {db_manager.max_connections}")
    
    # 연결 종료
    db_manager.close_all_connections()


if __name__ == "__main__":
    main()
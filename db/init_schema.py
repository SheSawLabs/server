"""
Database Schema Initialization

각 API별로 분리된 스키마 파일들을 로드하여 데이터베이스를 초기화하는 모듈
"""

import os
import sys
import logging
from pathlib import Path

# config 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.db_connection import get_db_manager

logger = logging.getLogger(__name__)


class SchemaInitializer:
    """데이터베이스 스키마 초기화 클래스"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.schemas_dir = Path(__file__).parent / 'schemas'
    
    def load_schema_file(self, schema_file: str) -> str:
        """스키마 파일 내용 로드"""
        file_path = self.schemas_dir / schema_file
        
        if not file_path.exists():
            raise FileNotFoundError(f"Schema file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def execute_schema(self, schema_sql: str, schema_name: str):
        """스키마 SQL 실행"""
        try:
            # SQL 문을 세미콜론으로 분리
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    self.db_manager.execute_non_query(statement)
            
            logger.info(f"Schema '{schema_name}' executed successfully")
            
        except Exception as e:
            logger.error(f"Failed to execute schema '{schema_name}': {e}")
            raise
    
    def init_all_schemas(self):
        """모든 스키마 파일 초기화"""
        schema_files = [
            'cctv_installations.sql',
            'safe_delivery_boxes.sql',
            'street_lights.sql',
            'sexual_offender_addresses.sql',
            'women_safety_houses.sql',
            'crime_safety_facilities.sql',
            'common_functions.sql'
        ]
        
        logger.info("Starting database schema initialization...")
        
        for schema_file in schema_files:
            try:
                schema_sql = self.load_schema_file(schema_file)
                schema_name = schema_file.replace('.sql', '')
                self.execute_schema(schema_sql, schema_name)
                
            except Exception as e:
                logger.error(f"Failed to initialize schema from {schema_file}: {e}")
                raise
        
        logger.info("All schemas initialized successfully")
    
    def init_specific_schema(self, schema_name: str):
        """특정 스키마만 초기화"""
        schema_file = f"{schema_name}.sql"
        
        try:
            schema_sql = self.load_schema_file(schema_file)
            self.execute_schema(schema_sql, schema_name)
            
        except Exception as e:
            logger.error(f"Failed to initialize schema '{schema_name}': {e}")
            raise
    
    def check_tables_exist(self) -> dict:
        """테이블 존재 여부 확인"""
        table_names = [
            'cctv_installations',
            'safe_delivery_boxes',
            'street_lights',
            'sexual_offender_addresses',
            'women_safety_houses',
            'crime_safety_facilities'
        ]
        
        results = {}
        
        for table_name in table_names:
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """
            
            try:
                result = self.db_manager.execute_query(query, (table_name,))
                results[table_name] = result[0]['exists']
                
            except Exception as e:
                logger.error(f"Failed to check table '{table_name}': {e}")
                results[table_name] = False
        
        return results


def main():
    """스키마 초기화 실행"""
    print("=== 데이터베이스 스키마 초기화 ===\n")
    
    initializer = SchemaInitializer()
    
    # 연결 테스트
    print("1. 데이터베이스 연결 테스트:")
    if initializer.db_manager.test_connection():
        print("   ✅ 연결 성공")
    else:
        print("   ❌ 연결 실패")
        return
    
    # 기존 테이블 확인
    print("\n2. 기존 테이블 확인:")
    existing_tables = initializer.check_tables_exist()
    for table_name, exists in existing_tables.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {table_name}")
    
    # 스키마 초기화
    print("\n3. 스키마 초기화:")
    try:
        initializer.init_all_schemas()
        print("   ✅ 모든 스키마 초기화 완료")
        
    except Exception as e:
        print(f"   ❌ 스키마 초기화 실패: {e}")
        return
    
    # 초기화 후 테이블 확인
    print("\n4. 초기화 후 테이블 확인:")
    updated_tables = initializer.check_tables_exist()
    for table_name, exists in updated_tables.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {table_name}")
    
    print("\n스키마 초기화가 완료되었습니다!")


if __name__ == "__main__":
    main()
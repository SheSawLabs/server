#!/usr/bin/env python3
"""
Seoul Safety Data Pipeline - Main Entry Point

서울 안전 데이터 파이프라인의 메인 실행 스크립트
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# 프로젝트 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from db.db_connection import get_db_manager
from db.init_schema import SchemaInitializer
from controllers.cctv_controller import CCTVController

logger = logging.getLogger(__name__)


class SafetyDataPipeline:
    """서울 안전 데이터 파이프라인 메인 클래스"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.schema_initializer = SchemaInitializer()
        
        # 컨트롤러 초기화
        self.controllers = {
            'cctv': CCTVController(),
            # 추후 다른 컨트롤러들 추가
            # 'delivery_box': DeliveryBoxController(),
            # 'streetlight': StreetlightController(),
            # 'sexual_offender': SexualOffenderController(),
            # 'women_safety': WomenSafetyController(),
            # 'crime_facility': CrimeFacilityController(),
        }
    
    def check_prerequisites(self) -> bool:
        """실행 전 필수 조건 확인"""
        logger.info("Checking prerequisites...")
        
        # 1. 필수 설정 확인
        validation = settings.validate_required_settings()
        missing_settings = [name for name, result in validation.items() if not result['is_set']]
        
        if missing_settings:
            logger.error(f"Missing required settings: {missing_settings}")
            return False
        
        # 2. 데이터베이스 연결 확인
        if not self.db_manager.test_connection():
            logger.error("Database connection failed")
            return False
        
        logger.info("Prerequisites check passed")
        return True
    
    def initialize_database(self) -> bool:
        """데이터베이스 스키마 초기화"""
        logger.info("Initializing database schema...")
        
        try:
            self.schema_initializer.init_all_schemas()
            logger.info("Database schema initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database schema initialization failed: {e}")
            return False
    
    def run_data_collection(self, data_types: list = None) -> dict:
        """데이터 수집 실행"""
        if data_types is None:
            data_types = list(self.controllers.keys())
        
        results = {}
        
        logger.info(f"Starting data collection for: {data_types}")
        
        for data_type in data_types:
            if data_type not in self.controllers:
                logger.warning(f"Unknown data type: {data_type}")
                continue
            
            logger.info(f"Collecting {data_type} data...")
            
            try:
                controller = self.controllers[data_type]
                result = controller.run_update()
                results[data_type] = result
                
                if result['success']:
                    logger.info(f"{data_type} data collection completed: {result['records_saved']} records")
                else:
                    logger.error(f"{data_type} data collection failed: {result['error']}")
                    
            except Exception as e:
                logger.error(f"Error collecting {data_type} data: {e}")
                results[data_type] = {
                    'success': False,
                    'error': str(e),
                    'records_fetched': 0,
                    'records_saved': 0
                }
        
        return results
    
    def generate_report(self, results: dict):
        """실행 결과 보고서 생성"""
        logger.info("Generating execution report...")
        
        total_fetched = sum(r.get('records_fetched', 0) for r in results.values())
        total_saved = sum(r.get('records_saved', 0) for r in results.values())
        successful_tasks = sum(1 for r in results.values() if r.get('success', False))
        
        report = f"""
========================================
Seoul Safety Data Pipeline - Execution Report
========================================
Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Overall Summary:
- Total Tasks: {len(results)}
- Successful Tasks: {successful_tasks}
- Failed Tasks: {len(results) - successful_tasks}
- Total Records Fetched: {total_fetched}
- Total Records Saved: {total_saved}

Task Details:
"""
        
        for data_type, result in results.items():
            status = "✅ SUCCESS" if result.get('success') else "❌ FAILED"
            report += f"""
- {data_type.upper()}:
  Status: {status}
  Records Fetched: {result.get('records_fetched', 0)}
  Records Saved: {result.get('records_saved', 0)}
  Execution Time: {result.get('execution_time', 0):.2f}s
"""
            if not result.get('success') and result.get('error'):
                report += f"  Error: {result['error']}\n"
        
        report += "\n========================================\n"
        
        # 콘솔 출력
        print(report)
        
        # 파일 저장
        report_file = f"execution_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report saved to: {report_file}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
    
    def run(self, data_types: list = None, init_db: bool = False, skip_prereq: bool = False):
        """파이프라인 전체 실행"""
        logger.info("Starting Seoul Safety Data Pipeline...")
        
        try:
            # 1. 필수 조건 확인
            if not skip_prereq and not self.check_prerequisites():
                logger.error("Prerequisites check failed. Aborting.")
                return False
            
            # 2. 데이터베이스 초기화 (옵션)
            if init_db:
                if not self.initialize_database():
                    logger.error("Database initialization failed. Aborting.")
                    return False
            
            # 3. 데이터 수집
            results = self.run_data_collection(data_types)
            
            # 4. 보고서 생성
            self.generate_report(results)
            
            # 5. 성공 여부 확인
            successful_tasks = sum(1 for r in results.values() if r.get('success', False))
            
            if successful_tasks == len(results):
                logger.info("Pipeline completed successfully!")
                return True
            else:
                logger.warning(f"Pipeline completed with {len(results) - successful_tasks} failed tasks")
                return False
                
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return False
        
        finally:
            # 연결 정리
            self.db_manager.close_all_connections()


def main():
    """메인 함수 - 명령행 인터페이스"""
    parser = argparse.ArgumentParser(description='Seoul Safety Data Pipeline')
    
    parser.add_argument(
        '--data-types', 
        nargs='+',
        choices=['cctv'],  # 추후 확장: 'delivery_box', 'streetlight', 'sexual_offender', 'women_safety', 'crime_facility'
        help='Data types to collect (default: all available)'
    )
    
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize database schema before data collection'
    )
    
    parser.add_argument(
        '--skip-prereq',
        action='store_true',
        help='Skip prerequisites check'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode (connection and setup check only)'
    )
    
    args = parser.parse_args()
    
    # 로깅 레벨 설정
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 파이프라인 실행
    pipeline = SafetyDataPipeline()
    
    if args.test:
        # 테스트 모드
        print("=== Seoul Safety Data Pipeline - Test Mode ===\n")
        
        print("1. Settings Check:")
        validation = settings.validate_required_settings()
        for setting_name, result in validation.items():
            status = "✅" if result['is_set'] else "❌"
            print(f"   {status} {setting_name}")
        
        print("\n2. Database Connection:")
        if pipeline.db_manager.test_connection():
            print("   ✅ Connection successful")
        else:
            print("   ❌ Connection failed")
        
        print("\n3. Available Controllers:")
        for controller_name in pipeline.controllers.keys():
            print(f"   - {controller_name}")
        
        print("\nTest completed.")
        
    else:
        # 실제 실행
        success = pipeline.run(
            data_types=args.data_types,
            init_db=args.init_db,
            skip_prereq=args.skip_prereq
        )
        
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
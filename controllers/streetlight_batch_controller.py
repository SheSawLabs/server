#!/usr/bin/env python3
"""
가로등 배치 처리 컨트롤러 - 일일 API 제한 고려

일일 100,000회 제한을 고려하여 배치로 나누어 처리
"""

import logging
import sys
import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers.streetlight_controller import StreetlightController

logger = logging.getLogger(__name__)


class StreetlightBatchController(StreetlightController):
    """가로등 배치 처리 컨트롤러"""
    
    def __init__(self):
        super().__init__()
        
        # 배치 처리 설정
        self.daily_limit = 95000  # 여유분 고려하여 95,000으로 설정
        self.batch_size = 1000    # 한 번에 처리할 레코드 수
        
    def fetch_data_batch(self, start_page: int = 1, max_records: int = None) -> List[Dict[str, Any]]:
        """
        배치 단위로 데이터 가져오기
        
        Args:
            start_page: 시작 페이지
            max_records: 최대 처리할 레코드 수 (None이면 제한 없음)
        """
        logger.info(f"Starting batch fetch from page {start_page}, max_records: {max_records}")
        
        if not self.api_key:
            logger.error("SEOUL_STREETLIGHT_API_KEY not configured")
            return []
        
        try:
            all_data = []
            page = start_page
            processed_count = 0
            
            while True:
                # 페이지 단위로 가져오기
                response = self.odcloud_client.fetch_page(
                    service_id=self.service_id,
                    api_key=self.api_key,
                    page=page,
                    per_page=1000
                )
                
                if not response or not response.get('data'):
                    logger.info(f"No more data on page {page}, stopping")
                    break
                
                raw_records = response['data']
                logger.info(f"Fetched page {page}: {len(raw_records)} raw records")
                
                # 배치 처리
                batch_processed = []
                for record in raw_records:
                    if max_records and processed_count >= max_records:
                        logger.info(f"Reached max_records limit: {max_records}")
                        break
                        
                    processed_record = self.process_record(record)
                    if processed_record:
                        batch_processed.append(processed_record)
                        processed_count += 1
                        
                    # API 호출 제한 체크 (지오코딩 호출 고려)
                    if processed_count >= self.daily_limit:
                        logger.warning(f"Approaching daily API limit ({self.daily_limit}), stopping")
                        break
                
                all_data.extend(batch_processed)
                logger.info(f"Processed {len(batch_processed)} records from page {page} (total: {len(all_data)})")
                
                # 중단 조건 체크
                if max_records and processed_count >= max_records:
                    break
                if processed_count >= self.daily_limit:
                    break
                if len(raw_records) < 1000:  # 마지막 페이지
                    break
                    
                page += 1
            
            logger.info(f"Batch fetch completed: {len(all_data)} total processed records")
            return all_data
            
        except Exception as e:
            logger.error(f"Error in batch fetch: {e}")
            return []
    
    def run_batch_update(self, max_records: int = None, start_page: int = 1) -> Dict[str, Any]:
        """
        배치 업데이트 실행
        
        Args:
            max_records: 최대 처리할 레코드 수
            start_page: 시작 페이지
        """
        logger.info(f"Starting batch update - max_records: {max_records}, start_page: {start_page}")
        
        start_time = time.time()
        result = {
            'success': False,
            'records_fetched': 0,
            'records_saved': 0,
            'execution_time': 0,
            'error': None,
            'api_calls_used': 0
        }
        
        try:
            # 1. 배치로 데이터 가져오기
            data = self.fetch_data_batch(start_page=start_page, max_records=max_records)
            result['records_fetched'] = len(data)
            result['api_calls_used'] = len(data)  # 지오코딩 API 호출 수
            
            if not data:
                result['error'] = "No data fetched from API"
                return result
            
            # 2. 데이터베이스에 저장 (기존 데이터 유지하고 추가)
            saved_count = self.save_to_database_append(data)
            result['records_saved'] = saved_count
            
            # 3. 성공 처리
            result['success'] = True
            result['execution_time'] = time.time() - start_time
            
            logger.info(f"Batch update completed: {saved_count} records saved, {result['api_calls_used']} API calls used")
            
        except Exception as e:
            result['error'] = str(e)
            result['execution_time'] = time.time() - start_time
            logger.error(f"Batch update failed: {e}")
        
        return result
    
    def save_to_database_append(self, data: List[Dict[str, Any]]) -> int:
        """기존 데이터에 추가하여 저장 (전체 삭제하지 않고)"""
        if not data:
            logger.warning("No data to save")
            return 0
        
        logger.info(f"Appending {len(data)} streetlight records to database")
        
        try:
            # 중복 방지를 위한 UPSERT 쿼리
            upsert_query = """
                INSERT INTO streetlight_installations (management_number, district, dong, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (management_number) DO UPDATE SET
                    district = EXCLUDED.district,
                    dong = EXCLUDED.dong,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 데이터 준비
            insert_data = []
            for record in data:
                insert_data.append((
                    record.get('management_number'),
                    record.get('district'),
                    record.get('dong'),
                    record.get('latitude'),
                    record.get('longitude')
                ))
            
            # 배치 삽입
            inserted_count = self.db_manager.execute_many(upsert_query, insert_data)
            logger.info(f"Upserted {inserted_count} records")
            
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            # management_number에 unique constraint가 없다면 일반 INSERT 사용
            try:
                logger.info("Trying regular INSERT without conflict resolution")
                insert_query = """
                    INSERT INTO streetlight_installations (management_number, district, dong, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                insert_data = []
                for record in data:
                    insert_data.append((
                        record.get('management_number'),
                        record.get('district'),
                        record.get('dong'),
                        record.get('latitude'),
                        record.get('longitude')
                    ))
                
                inserted_count = self.db_manager.execute_many(insert_query, insert_data)
                logger.info(f"Inserted {inserted_count} records (regular INSERT)")
                return inserted_count
                
            except Exception as e2:
                logger.error(f"Error with regular INSERT: {e2}")
                raise
    
    def get_progress_info(self) -> Dict[str, Any]:
        """처리 진행 상황 조회"""
        try:
            # 현재 저장된 데이터 수
            stats = self.get_statistics()
            current_count = stats.get('total_streetlights', 0)
            
            # 전체 데이터 수 (API에서 확인)
            response = self.odcloud_client.fetch_page(
                service_id=self.service_id,
                api_key=self.api_key,
                page=1,
                per_page=1
            )
            
            total_count = response.get('totalCount', 0) if response else 0
            
            return {
                'current_count': current_count,
                'total_count': total_count,
                'progress_percentage': (current_count / total_count * 100) if total_count > 0 else 0,
                'remaining_count': total_count - current_count
            }
            
        except Exception as e:
            logger.error(f"Error getting progress info: {e}")
            return {}


def main():
    """배치 컨트롤러 테스트"""
    print("=== 가로등 배치 처리 컨트롤러 테스트 ===\n")
    
    controller = StreetlightBatchController()
    
    # 1. 설정 확인
    print("1. 설정 확인:")
    print(f"   일일 제한: {controller.daily_limit:,}회")
    print(f"   배치 크기: {controller.batch_size:,}개")
    print(f"   API 키: {'✅' if controller.api_key else '❌'}")
    
    # 2. 진행 상황 확인
    print(f"\n2. 현재 진행 상황:")
    progress = controller.get_progress_info()
    if progress:
        print(f"   저장된 데이터: {progress['current_count']:,}개")
        print(f"   전체 데이터: {progress['total_count']:,}개")
        print(f"   진행률: {progress['progress_percentage']:.1f}%")
        print(f"   남은 데이터: {progress['remaining_count']:,}개")
    
    # 3. 배치 처리 실행 (1000개만 테스트)
    print(f"\n3. 배치 처리 테스트 (1000개):")
    result = controller.run_batch_update(max_records=1000)
    
    if result['success']:
        print(f"   ✅ 처리 성공!")
        print(f"   가져온 레코드: {result['records_fetched']:,}개")
        print(f"   저장된 레코드: {result['records_saved']:,}개")
        print(f"   API 호출 수: {result['api_calls_used']:,}회")
        print(f"   실행 시간: {result['execution_time']:.2f}초")
        
        # 업데이트 후 진행 상황
        print(f"\n4. 업데이트 후 진행 상황:")
        progress_after = controller.get_progress_info()
        if progress_after:
            print(f"   저장된 데이터: {progress_after['current_count']:,}개")
            print(f"   진행률: {progress_after['progress_percentage']:.1f}%")
    else:
        print(f"   ❌ 처리 실패: {result['error']}")


if __name__ == "__main__":
    main()
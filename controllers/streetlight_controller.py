"""
가로등 위치 정보 API 컨트롤러

공공데이터포털 가로등 위치 데이터를 수집하고 PostgreSQL에 저장
"""

import logging
import sys
import os
from typing import List, Dict, Any, Optional
import time

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.odcloud_api import ODCloudAPIClient
from utils.geocoding import EnhancedAddressParser
from db.db_connection import get_db_manager
from config.settings import settings

logger = logging.getLogger(__name__)


class StreetlightController:
    """가로등 위치 정보 API 컨트롤러"""
    
    def __init__(self):
        self.odcloud_client = ODCloudAPIClient()
        self.db_manager = get_db_manager()
        self.address_parser = EnhancedAddressParser()
        
        # 가로등 API 설정
        self.service_id = "15107934/v1/uddi:20b10130-21ed-43f3-8e58-b8692fb8a2ff"
        self.api_key = settings.SEOUL_STREETLIGHT_API_KEY
        
        # API 필드 -> DB 필드 매핑 (한글 필드명)
        self.field_mapping = {
            '관리번호': 'management_number',    # 관리번호
            '위도': 'latitude',              # 위도
            '경도': 'longitude',             # 경도
        }
        
        # 대체 필드명
        self.alternative_fields = {
            'management_number': ['관리번호', 'MANAGEMENT_NUMBER', 'ID', 'NUMBER'],
            'latitude': ['위도', 'LAT', 'LATITUDE', 'Y'],
            'longitude': ['경도', 'LON', 'LONGITUDE', 'X'],
        }
    
    def find_field_value(self, record: Dict[str, Any], field_type: str) -> Any:
        """레코드에서 필드 값 찾기 (대체 필드명 고려)"""
        for field_name in self.alternative_fields.get(field_type, []):
            if field_name in record and record[field_name]:
                return record[field_name]
        return None
    
    def process_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """개별 레코드 처리"""
        try:
            # 각 필드별로 값 찾기
            processed_data = {}
            
            for db_field in ['management_number', 'latitude', 'longitude']:
                value = self.find_field_value(record, db_field)
                
                if db_field == 'latitude':
                    try:
                        processed_data[db_field] = float(value) if value else None
                    except (ValueError, TypeError):
                        processed_data[db_field] = None
                        
                elif db_field == 'longitude':
                    try:
                        processed_data[db_field] = float(value) if value else None
                    except (ValueError, TypeError):
                        processed_data[db_field] = None
                        
                else:  # 문자열 필드
                    processed_data[db_field] = str(value).strip() if value else None
            
            # 좌표 기반 지오코딩으로 자치구 및 동명 추출
            district = None
            dong = None
            
            lat, lon = processed_data.get('latitude'), processed_data.get('longitude')
            if lat and lon:
                parsed_address = self.address_parser.parse_with_coordinates(
                    '',  # 주소 정보가 없으므로 빈 문자열
                    lat, lon
                )
                
                if parsed_address['parsing_success']:
                    district = parsed_address['district']
                    dong = parsed_address['dong']
                    
                    # 디버그 로그
                    logger.debug(f"Geocoding method: {parsed_address.get('method', 'unknown')}")
            
            processed_data['district'] = district
            processed_data['dong'] = dong
            
            # 필수 데이터 검증 (좌표가 있어야 함)
            if not processed_data.get('latitude') or not processed_data.get('longitude'):
                logger.warning("Record missing coordinates, skipping")
                return None
            
            # 좌표 유효성 검사
            if lat and lon:
                # 대한민국 좌표 범위 확인 (대략적)
                if not (33.0 <= lat <= 43.0 and 124.0 <= lon <= 132.0):
                    logger.warning(f"Invalid coordinates ({lat}, {lon}) for management_number: {processed_data.get('management_number', 'Unknown')}")
                    return None
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing record: {e}")
            return None
    
    def fetch_data(self) -> List[Dict[str, Any]]:
        """API에서 가로등 데이터 가져오기"""
        logger.info(f"Fetching streetlight data from API service: {self.service_id}")
        
        if not self.api_key:
            logger.error("SEOUL_STREETLIGHT_API_KEY not configured")
            return []
        
        try:
            # 모든 페이지 데이터 가져오기
            raw_data = self.odcloud_client.fetch_all_pages(
                service_id=self.service_id,
                api_key=self.api_key,
                max_pages=50,  # 안전장치 (필요시 조정)
                per_page=1000
            )
            
            if not raw_data:
                logger.warning("No data fetched from API")
                return []
            
            logger.info(f"Fetched {len(raw_data)} raw records")
            
            # 데이터 처리
            processed_data = []
            for record in raw_data:
                processed_record = self.process_record(record)
                if processed_record:
                    processed_data.append(processed_record)
            
            logger.info(f"Processed {len(processed_data)} valid records")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching streetlight data: {e}")
            return []
    
    def save_to_database(self, data: List[Dict[str, Any]]) -> int:
        """데이터베이스에 데이터 저장"""
        if not data:
            logger.warning("No data to save")
            return 0
        
        logger.info(f"Saving {len(data)} streetlight records to database")
        
        try:
            # 기존 데이터 삭제 (전체 갱신 방식)
            delete_query = "DELETE FROM streetlight_installations"
            deleted_count = self.db_manager.execute_non_query(delete_query)
            logger.info(f"Deleted {deleted_count} existing records")
            
            # 새 데이터 삽입
            insert_query = """
                INSERT INTO streetlight_installations (management_number, district, dong, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s)
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
            inserted_count = self.db_manager.execute_many(insert_query, insert_data)
            logger.info(f"Inserted {inserted_count} new records")
            
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            raise
    
    def run_update(self) -> Dict[str, Any]:
        """가로등 데이터 업데이트 실행"""
        logger.info("Starting streetlight data update")
        
        start_time = time.time()
        result = {
            'success': False,
            'records_fetched': 0,
            'records_saved': 0,
            'execution_time': 0,
            'error': None
        }
        
        try:
            # 1. API에서 데이터 가져오기
            data = self.fetch_data()
            result['records_fetched'] = len(data)
            
            if not data:
                result['error'] = "No data fetched from API"
                return result
            
            # 2. 데이터베이스에 저장
            saved_count = self.save_to_database(data)
            result['records_saved'] = saved_count
            
            # 3. 성공 처리
            result['success'] = True
            result['execution_time'] = time.time() - start_time
            
            logger.info(f"Streetlight data update completed successfully: {saved_count} records")
            
        except Exception as e:
            result['error'] = str(e)
            result['execution_time'] = time.time() - start_time
            logger.error(f"Streetlight data update failed: {e}")
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """가로등 설치 현황 통계 조회"""
        try:
            # 전체 통계
            total_query = "SELECT COUNT(*) as total_count FROM streetlight_installations"
            total_result = self.db_manager.execute_query(total_query)
            
            # 자치구별 통계
            district_query = """
                SELECT district, COUNT(*) as streetlight_count
                FROM streetlight_installations 
                WHERE district IS NOT NULL
                GROUP BY district 
                ORDER BY streetlight_count DESC
            """
            district_result = self.db_manager.execute_query(district_query)
            
            # 동별 통계 (상위 10개)
            dong_query = """
                SELECT dong, COUNT(*) as streetlight_count
                FROM streetlight_installations 
                WHERE dong IS NOT NULL
                GROUP BY dong 
                ORDER BY streetlight_count DESC
                LIMIT 10
            """
            dong_result = self.db_manager.execute_query(dong_query)
            
            # 좌표 유무 통계
            coord_query = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as with_coords,
                    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL THEN 1 END) as without_coords
                FROM streetlight_installations
            """
            coord_result = self.db_manager.execute_query(coord_query)
            
            return {
                'total_streetlights': total_result[0]['total_count'],
                'by_district': district_result,
                'top_dongs': dong_result,
                'coordinates_stats': coord_result[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}


def main():
    """가로등 컨트롤러 테스트"""
    print("=== 가로등 컨트롤러 테스트 ===\n")
    
    controller = StreetlightController()
    
    # 1. 설정 확인
    print("1. 설정 확인:")
    print(f"   API 서비스 ID: {controller.service_id}")
    print(f"   API 키 설정: {'✅' if controller.api_key else '❌'}")
    
    # 2. 데이터베이스 연결 테스트
    print(f"\n2. 데이터베이스 연결:")
    if controller.db_manager.test_connection():
        print("   ✅ 연결 성공")
    else:
        print("   ❌ 연결 실패")
        return
    
    # 3. 기존 통계 조회
    print(f"\n3. 기존 데이터 통계:")
    stats = controller.get_statistics()
    if stats:
        print(f"   전체 가로등: {stats.get('total_streetlights', 0)}개")
        coord_stats = stats.get('coordinates_stats', {})
        print(f"   좌표 보유율: {coord_stats.get('with_coords', 0)}/{coord_stats.get('total', 0)}")
    else:
        print("   통계 조회 실패 또는 데이터 없음")
    
    # 4. 샘플 데이터 처리 테스트
    print(f"\n4. 샘플 데이터 처리:")
    sample_record = {
        '관리번호': 'SL-2024-001',
        '위도': '37.5665',
        '경도': '126.9780'
    }
    
    processed = controller.process_record(sample_record)
    if processed:
        print(f"   ✅ 처리 성공: {processed}")
    else:
        print(f"   ❌ 처리 실패")
    
    # 5. 실제 API 호출 및 업데이트 (선택적)
    print(f"\n5. 실제 데이터 업데이트:")
    if controller.api_key:
        user_input = input("   실제 API 호출을 실행하시겠습니까? (y/N): ")
        if user_input.lower() == 'y':
            print("   데이터 업데이트 실행 중...")
            result = controller.run_update()
            
            if result['success']:
                print(f"   ✅ 업데이트 성공!")
                print(f"   가져온 레코드: {result['records_fetched']}개")
                print(f"   저장된 레코드: {result['records_saved']}개")
                print(f"   실행 시간: {result['execution_time']:.2f}초")
            else:
                print(f"   ❌ 업데이트 실패: {result['error']}")
        else:
            print("   업데이트를 건너뜁니다.")
    else:
        print("   ❌ API 키가 설정되지 않아 실제 호출을 할 수 없습니다.")


if __name__ == "__main__":
    main()
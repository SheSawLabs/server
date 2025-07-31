#!/usr/bin/env python3
"""
전국 경찰서 지구대 파출소 주소 현황 데이터 수집 컨트롤러

CSV 파일에서 서울시 경찰서 데이터만 필터링하여 수집합니다.
"""

import csv
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import os

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_connection import DatabaseManager
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PoliceStationController:
    """경찰서 지구대 파출소 데이터 컨트롤러"""
    
    def __init__(self):
        """컨트롤러 초기화"""
        # 데이터베이스 연결
        self.db = DatabaseManager()
        
        # CSV 파일 경로 (프로젝트 루트 기준)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.csv_file_path = os.path.join(project_root, "경찰청_전국 지구대 파출소 주소 현황_20241231.csv")
        
        logger.info("PoliceStationController initialized")
    
    def read_csv_with_encoding(self, encoding: str = 'cp949') -> List[Dict[str, Any]]:
        """CSV 파일을 지정된 인코딩으로 읽기"""
        try:
            data = []
            with open(self.csv_file_path, 'r', encoding=encoding) as file:
                csv_reader = csv.DictReader(file)
                
                # 헤더 확인
                fieldnames = csv_reader.fieldnames
                logger.info(f"CSV headers detected: {fieldnames}")
                
                for row_num, row in enumerate(csv_reader, start=1):
                    if row_num > 50000:  # 메모리 절약을 위해 제한
                        break
                    data.append(row)
            
            logger.info(f"Successfully read {len(data)} records from CSV with {encoding} encoding")
            return data
            
        except UnicodeDecodeError as e:
            logger.error(f"Encoding error with {encoding}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return []
    
    def try_multiple_encodings(self) -> List[Dict[str, Any]]:
        """여러 인코딩을 시도하여 CSV 파일 읽기"""
        encodings = ['cp949', 'euc-kr', 'utf-8', 'utf-8-sig']
        
        for encoding in encodings:
            logger.info(f"Trying encoding: {encoding}")
            data = self.read_csv_with_encoding(encoding)
            
            if data:
                # 첫 번째 레코드를 확인하여 한글이 제대로 읽혔는지 검증
                first_record = data[0]
                test_value = str(first_record.get('시도청', '') or first_record.get(list(first_record.keys())[1], ''))
                
                # 한글 문자가 포함되어 있고, 깨진 문자가 없으면 성공
                if re.search(r'[가-힣]', test_value) and '�' not in test_value:
                    logger.info(f"✅ Successfully read CSV with {encoding} encoding")
                    logger.info(f"Sample data: {test_value}")
                    return data
                else:
                    logger.warning(f"Korean characters not properly decoded with {encoding}")
        
        logger.error("Failed to read CSV with any encoding")
        return []
    
    def filter_seoul_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """서울시 데이터만 필터링"""
        seoul_data = []
        
        for record in data:
            # 여러 가능한 컬럼명 확인
            city_province = (
                record.get('시도청', '') or 
                record.get('시도', '') or 
                record.get('광역시도', '') or
                ''
            )
            
            # 서울 관련 키워드 확인
            if '서울' in city_province:
                seoul_data.append(record)
        
        logger.info(f"Filtered {len(seoul_data)} Seoul records from {len(data)} total records")
        return seoul_data
    
    def process_raw_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """원시 데이터를 처리하여 표준화된 형태로 변환"""
        processed_data = []
        
        for item in raw_data:
            try:
                # 컬럼명 매핑 (여러 가능한 이름 시도)
                sequence_number = item.get('순번', '') or item.get('번호', '') or ''
                city_province = item.get('시도청', '') or item.get('시도', '') or ''
                police_station = item.get('경찰서', '') or item.get('본서', '') or ''
                office_name = item.get('관서명', '') or item.get('파출소명', '') or item.get('지구대명', '') or ''
                office_type = item.get('구분', '') or item.get('분류', '') or ''
                phone_number = item.get('전화번호', '') or item.get('연락처', '') or ''
                address = item.get('주소', '') or item.get('소재지', '') or ''
                
                # 주소에서 동 정보 추출
                dong = self._extract_dong_from_address(address)
                
                # 구 정보 추출
                district = self._extract_district_from_address(address)
                
                processed_item = {
                    'sequence_number': str(sequence_number).strip(),
                    'city_province_name': str(city_province).strip(),
                    'police_station_name': str(police_station).strip(),
                    'office_name': str(office_name).strip(),
                    'office_type': str(office_type).strip(),
                    'phone_number': str(phone_number).strip(),
                    'full_address': str(address).strip(),
                    'district_name': district,
                    'dong_name': dong,
                    'latitude': None,  # 나중에 지오코딩
                    'longitude': None,
                    'geocoding_method': 'pending'
                }
                
                # 필수 필드 검증
                if not processed_item['office_name'] or not processed_item['full_address']:
                    logger.warning(f"Skipping item with missing required fields: {item}")
                    continue
                
                processed_data.append(processed_item)
                
            except Exception as e:
                logger.error(f"Error processing item {item}: {e}")
                continue
        
        logger.info(f"Processed {len(processed_data)} police station records")
        return processed_data
    
    def save_to_database(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """처리된 데이터를 데이터베이스에 저장"""
        if not data:
            return {'success': True, 'saved_count': 0}
        
        try:
            # 테이블 생성 (없는 경우)
            self._ensure_table_exists()
            
            # UPSERT 쿼리 (중복 방지)
            insert_query = """
            INSERT INTO police_stations (
                sequence_number, city_province_name, police_station_name, office_name,
                office_type, phone_number, full_address, district_name, dong_name,
                latitude, longitude, geocoding_method
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (office_name, full_address) DO UPDATE SET
                sequence_number = EXCLUDED.sequence_number,
                city_province_name = EXCLUDED.city_province_name,
                police_station_name = EXCLUDED.police_station_name,
                office_type = EXCLUDED.office_type,
                phone_number = EXCLUDED.phone_number,
                district_name = EXCLUDED.district_name,
                dong_name = EXCLUDED.dong_name,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                geocoding_method = EXCLUDED.geocoding_method,
                updated_at = CURRENT_TIMESTAMP
            """
            
            # 데이터 준비
            values = []
            for item in data:
                values.append((
                    item['sequence_number'],
                    item['city_province_name'],
                    item['police_station_name'],
                    item['office_name'],
                    item['office_type'],
                    item['phone_number'],
                    item['full_address'],
                    item['district_name'],
                    item['dong_name'],
                    item['latitude'],
                    item['longitude'],
                    item['geocoding_method']
                ))
            
            # 배치 삽입 실행
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(insert_query, values)
                    saved_count = cursor.rowcount
                    conn.commit()
            
            logger.info(f"Upserted {saved_count} police station records")
            return {'success': True, 'saved_count': saved_count}
            
        except Exception as e:
            logger.error(f"Error saving data to database: {e}")
            return {'success': False, 'error': str(e), 'saved_count': 0}
    
    def _ensure_table_exists(self):
        """경찰서 테이블 생성"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS police_stations (
            id SERIAL PRIMARY KEY,
            sequence_number VARCHAR(10),
            city_province_name VARCHAR(50) NOT NULL,
            police_station_name VARCHAR(100) NOT NULL,
            office_name VARCHAR(100) NOT NULL,
            office_type VARCHAR(20),
            phone_number VARCHAR(20),
            full_address TEXT NOT NULL,
            district_name VARCHAR(50),
            dong_name VARCHAR(50),
            latitude DECIMAL(10, 7),
            longitude DECIMAL(10, 7),
            geocoding_method VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(office_name, full_address)
        );
        
        CREATE INDEX IF NOT EXISTS idx_police_stations_location 
        ON police_stations(city_province_name, district_name, dong_name);
        
        CREATE INDEX IF NOT EXISTS idx_police_stations_coords 
        ON police_stations(latitude, longitude);
        
        CREATE INDEX IF NOT EXISTS idx_police_stations_type 
        ON police_stations(office_type);
        """
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_table_query)
                    conn.commit()
            logger.info("Police stations table ensured")
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            raise
    
    def _extract_dong_from_address(self, address: str) -> Optional[str]:
        """주소에서 동 정보 추출"""
        if not address:
            return None
            
        # 동 패턴 매칭
        dong_patterns = [
            r'([가-힣]+(?:동|가동|로동))',  # 기본 동 패턴
            r'([가-힣]+(?:면|리))',        # 면, 리 패턴
            r'([가-힣]+(?:가))',           # 가 패턴
        ]
        
        for pattern in dong_patterns:
            matches = re.findall(pattern, address)
            if matches:
                dong = matches[0]
                logger.debug(f"Extracted dong '{dong}' from address: {address}")
                return dong
        
        logger.debug(f"Could not extract dong from address: {address}")
        return None
    
    def _extract_district_from_address(self, address: str) -> Optional[str]:
        """주소에서 구 정보 추출"""
        if not address:
            return None
            
        # 구 패턴 매칭
        district_patterns = [
            r'([가-힣]+구)',  # 기본 구 패턴
            r'([가-힣]+시)',  # 시 패턴 (구가 없는 경우)
        ]
        
        for pattern in district_patterns:
            matches = re.findall(pattern, address)
            if matches:
                district = matches[0]
                logger.debug(f"Extracted district '{district}' from address: {address}")
                return district
        
        logger.debug(f"Could not extract district from address: {address}")
        return None
    
    def get_progress_info(self) -> Dict[str, Any]:
        """현재 수집 진행 상황 조회"""
        try:
            # 현재 저장된 데이터 수 조회
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) as count FROM police_stations")
                    result = cursor.fetchone()
                    current_count = result['count'] if result else 0
                    
                    # 타입별 통계
                    cursor.execute("""
                        SELECT 
                            office_type,
                            COUNT(*) as count
                        FROM police_stations 
                        GROUP BY office_type
                        ORDER BY count DESC
                    """)
                    type_stats = cursor.fetchall()
            
            return {
                'current_count': current_count,
                'type_statistics': type_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting progress info: {e}")
            return {
                'current_count': 0,
                'type_statistics': []
            }
    
    def run_full_collection(self) -> Dict[str, Any]:
        """전체 서울시 경찰서 데이터 수집"""
        logger.info("Starting Seoul police station data collection from CSV")
        
        try:
            # CSV 파일 읽기
            logger.info("Reading CSV file with multiple encoding attempts...")
            raw_data = self.try_multiple_encodings()
            
            if not raw_data:
                return {
                    'success': False,
                    'error': 'Failed to read CSV file with any encoding',
                    'records_processed': 0,
                    'records_saved': 0
                }
            
            # 서울시 데이터 필터링
            seoul_data = self.filter_seoul_data(raw_data)
            
            if not seoul_data:
                return {
                    'success': False,
                    'error': 'No Seoul data found in CSV',
                    'records_processed': 0,
                    'records_saved': 0
                }
            
            # 데이터 처리
            processed_data = self.process_raw_data(seoul_data)
            
            if not processed_data:
                return {
                    'success': False,
                    'error': 'No valid data after processing',
                    'records_processed': 0,
                    'records_saved': 0
                }
            
            # 데이터베이스 저장
            save_result = self.save_to_database(processed_data)
            
            if save_result['success']:
                logger.info(f"Seoul police station collection completed: {len(processed_data)} records processed, {save_result['saved_count']} records saved")
                
                return {
                    'success': True,
                    'records_processed': len(processed_data),
                    'records_saved': save_result['saved_count']
                }
            else:
                return {
                    'success': False,
                    'error': save_result.get('error', 'Database save failed'),
                    'records_processed': len(processed_data),
                    'records_saved': 0
                }
            
        except Exception as e:
            logger.error(f"Error in full collection: {e}")
            return {
                'success': False,
                'error': str(e),
                'records_processed': 0,
                'records_saved': 0
            }


def main():
    """테스트 실행"""
    print("🚔 Seoul Police Station Controller Test")
    print("=" * 60)
    
    controller = PoliceStationController()
    
    # 진행 상황 확인
    progress = controller.get_progress_info()
    print(f"\n📊 Current Progress:")
    print(f"   Saved: {progress['current_count']:,} records")
    
    if progress['type_statistics']:
        print(f"   By Type:")
        for stat in progress['type_statistics']:
            print(f"     {stat['office_type']}: {stat['count']:,} records")
    
    # 전체 데이터 수집
    print(f"\n🧪 Starting full data collection...")
    result = controller.run_full_collection()
    
    if result['success']:
        print(f"✅ Collection completed successfully!")
        print(f"   Records processed: {result['records_processed']}")
        print(f"   Records saved: {result['records_saved']}")
        
        # 업데이트된 진행 상황
        progress_after = controller.get_progress_info()
        print(f"\n📊 Final Status:")
        print(f"   Total saved: {progress_after['current_count']:,} records")
        
        if progress_after['type_statistics']:
            print(f"   By Type:")
            for stat in progress_after['type_statistics']:
                print(f"     {stat['office_type']}: {stat['count']:,} records")
        
    else:
        print(f"❌ Collection failed: {result.get('error')}")


if __name__ == "__main__":
    main()
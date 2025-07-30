"""
Common API Utilities

공통 API 호출 및 데이터 처리 유틸리티
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Any, Union
import json
import sys
import os

# config 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

logger = logging.getLogger(__name__)


class APIClient:
    """공통 API 클라이언트"""
    
    def __init__(self, request_delay: float = None):
        """
        API 클라이언트 초기화
        
        Args:
            request_delay: 요청 간 지연 시간 (초)
        """
        self.request_delay = request_delay or settings.API_REQUEST_DELAY
        self.timeout = settings.API_TIMEOUT
        self.max_retries = settings.API_MAX_RETRIES
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Seoul Safety Data Pipeline/1.0',
            'Accept': 'application/json'
        })
    
    def make_request(self, url: str, params: Dict[str, Any] = None, method: str = 'GET') -> Optional[Dict]:
        """
        HTTP 요청 실행
        
        Args:
            url: 요청 URL
            params: 요청 파라미터
            method: HTTP 메소드
            
        Returns:
            응답 JSON 데이터 또는 None
        """
        for attempt in range(self.max_retries):
            try:
                # 요청 지연
                if attempt > 0:
                    time.sleep(self.request_delay * (2 ** attempt))  # 지수 백오프
                else:
                    time.sleep(self.request_delay)
                
                # HTTP 요청
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout
                )
                
                # 응답 상태 확인
                if response.status_code == 200:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON response from {url}")
                        return None
                        
                elif response.status_code == 429:
                    # Rate limit - 더 오래 기다림
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"Rate limited, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                else:
                    logger.error(f"HTTP {response.status_code} error from {url}: {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries}): {url}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error (attempt {attempt + 1}/{self.max_retries}): {e}")
        
        logger.error(f"Failed to fetch data from {url} after {self.max_retries} attempts")
        return None
    
    def fetch_seoul_api_data(self, service_name: str, start_idx: int = 1, end_idx: int = 1000) -> Optional[Dict]:
        """
        서울 열린데이터 API 호출
        
        Args:
            service_name: API 서비스명
            start_idx: 시작 인덱스
            end_idx: 종료 인덱스
            
        Returns:
            API 응답 데이터
        """
        if not settings.SEOUL_OPEN_API_KEY:
            logger.error("Seoul Open API key not found")
            return None
        
        url = settings.get_seoul_api_url(service_name, start_idx, end_idx)
        return self.make_request(url)
    
    def fetch_all_pages(self, service_name: str, page_size: int = 1000) -> List[Dict]:
        """
        모든 페이지 데이터를 가져오기
        
        Args:
            service_name: API 서비스명
            page_size: 페이지 크기
            
        Returns:
            전체 데이터 리스트
        """
        all_data = []
        start_idx = 1
        
        while True:
            end_idx = start_idx + page_size - 1
            
            logger.info(f"Fetching {service_name}: {start_idx}-{end_idx}")
            
            response = self.fetch_seoul_api_data(service_name, start_idx, end_idx)
            
            if not response:
                logger.warning(f"No response for {service_name} at {start_idx}-{end_idx}")
                break
            
            # 응답 구조 파싱 (서울 열린데이터 API 형식)
            try:
                # API 응답에서 실제 데이터 추출
                service_key = list(response.keys())[0]
                data = response[service_key]
                
                # 에러 체크
                if 'RESULT' in data:
                    result_code = data['RESULT'].get('CODE', '')
                    if result_code != 'INFO-000':
                        logger.error(f"API error: {data['RESULT'].get('MESSAGE', 'Unknown error')}")
                        break
                
                # 실제 데이터 행 추출
                rows = data.get('row', [])
                if not rows:
                    logger.info(f"No more data available for {service_name}")
                    break
                
                all_data.extend(rows)
                
                # 다음 페이지로
                if len(rows) < page_size:
                    logger.info(f"Reached end of data for {service_name}")
                    break
                
                start_idx = end_idx + 1
                
            except (KeyError, IndexError, TypeError) as e:
                logger.error(f"Error parsing response for {service_name}: {e}")
                break
        
        logger.info(f"Fetched total {len(all_data)} records for {service_name}")
        return all_data


class DataProcessor:
    """데이터 처리 유틸리티"""
    
    @staticmethod
    def extract_location_info(record: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        레코드에서 위치 정보 추출
        
        Args:
            record: 원본 데이터 레코드
            field_mapping: 필드 매핑 (API 필드명 -> DB 필드명)
            
        Returns:
            위치 정보 딕셔너리
        """
        location_data = {}
        
        for api_field, db_field in field_mapping.items():
            value = record.get(api_field, '')
            
            # 좌표 데이터 처리
            if db_field in ['latitude', 'longitude']:
                try:
                    location_data[db_field] = float(value) if value else None
                except (ValueError, TypeError):
                    location_data[db_field] = None
            
            # 숫자 데이터 처리
            elif db_field in ['cctv_count']:
                try:
                    location_data[db_field] = int(value) if value else 1
                except (ValueError, TypeError):
                    location_data[db_field] = 1
            
            # 문자열 데이터 처리
            else:
                location_data[db_field] = str(value).strip() if value else None
        
        return location_data
    
    @staticmethod
    def clean_address(address: str) -> str:
        """주소 정리"""
        if not address:
            return ''
        
        # 불필요한 공백 제거
        address = ' '.join(address.split())
        
        # '서울특별시' 제거 (중복 방지)
        if address.startswith('서울특별시 '):
            address = address[6:]
        elif address.startswith('서울시 '):
            address = address[4:]
        
        return address
    
    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:
        """좌표 유효성 검사 (서울 지역 범위)"""
        if not latitude or not longitude:
            return False
        
        # 서울 지역 대략적 범위
        seoul_bounds = {
            'min_lat': 37.4,
            'max_lat': 37.7,
            'min_lon': 126.7,
            'max_lon': 127.3
        }
        
        return (seoul_bounds['min_lat'] <= latitude <= seoul_bounds['max_lat'] and
                seoul_bounds['min_lon'] <= longitude <= seoul_bounds['max_lon'])


def main():
    """유틸리티 테스트"""
    print("=== API 유틸리티 테스트 ===\n")
    
    # API 클라이언트 테스트
    client = APIClient()
    
    print("1. API 클라이언트 설정:")
    print(f"   Request Delay: {client.request_delay}초")
    print(f"   Timeout: {client.timeout}초")
    print(f"   Max Retries: {client.max_retries}회")
    
    # 샘플 API 호출 (실제 서비스명으로 변경 필요)
    print(f"\n2. 샘플 API 호출:")
    if settings.SEOUL_OPEN_API_KEY:
        print("   API 키가 설정되어 있습니다.")
    else:
        print("   ❌ API 키가 설정되지 않았습니다.")
    
    # 데이터 처리 테스트
    print(f"\n3. 데이터 처리 테스트:")
    
    sample_record = {
        'ADDR': '서울특별시 강남구 테헤란로 212',
        'LAT': '37.5048',
        'LOT': '127.0438',
        'CCTV_CNT': '3'
    }
    
    field_mapping = {
        'ADDR': 'address',
        'LAT': 'latitude', 
        'LOT': 'longitude',
        'CCTV_CNT': 'cctv_count'
    }
    
    processed = DataProcessor.extract_location_info(sample_record, field_mapping)
    print(f"   처리된 데이터: {processed}")
    
    # 좌표 유효성 검사
    if processed.get('latitude') and processed.get('longitude'):
        is_valid = DataProcessor.validate_coordinates(processed['latitude'], processed['longitude'])
        print(f"   좌표 유효성: {'✅' if is_valid else '❌'}")


if __name__ == "__main__":
    main()
"""
지오코딩 유틸리티

좌표를 이용한 역지오코딩으로 행정동 정보를 가져오는 기능
카카오 로컬 API 사용
"""

import requests
import logging
import time
from typing import Optional, Dict, Any, Tuple
import sys
import os

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

logger = logging.getLogger(__name__)


class KakaoGeocoder:
    """카카오 API를 이용한 지오코딩 클래스"""
    
    def __init__(self):
        self.api_key = settings.KAKAO_API_KEY
        self.base_url = "https://dapi.kakao.com/v2/local"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'KakaoAK {self.api_key}'
        })
        
        # API 호출 제한 (안전하게 초당 5회로 설정)
        self.last_request_time = 0
        self.min_interval = 0.2  # 200ms (초당 5회)
        self.daily_request_count = 0
        self.daily_limit = 250000  # 여유있게 설정 (실제 300,000)
        
    def coordinate_to_address(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """
        좌표를 주소로 변환 (역지오코딩)
        
        Args:
            latitude: 위도
            longitude: 경도
            
        Returns:
            주소 정보 딕셔너리 또는 None
        """
        if not self.api_key:
            logger.warning("Kakao API key not configured")
            return None
        
        try:
            # API 호출 제한 적용
            if not self._can_make_request():
                logger.warning("Daily API limit reached or rate limit exceeded")
                return None
            
            self._wait_for_rate_limit()
            
            url = f"{self.base_url}/geo/coord2address.json"
            params = {
                'x': longitude,
                'y': latitude,
                'input_coord': 'WGS84'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # 요청 카운트 증가
            self.daily_request_count += 1
            
            data = response.json()
            
            if data.get('documents'):
                # 첫 번째 결과 사용 (가장 정확한 결과)
                doc = data['documents'][0]
                
                # 도로명 주소와 지번 주소 모두 확인
                road_address = doc.get('road_address')
                address = doc.get('address')
                
                result = {
                    'latitude': latitude,
                    'longitude': longitude,
                    'district': None,
                    'dong': None,
                    'full_address': None,
                    'road_address': None,
                    'confidence': 0.8  # 좌표 기반이므로 높은 신뢰도
                }
                
                # 지번 주소와 도로명 주소 모두 확인해서 최적의 정보 조합
                district = None
                dong = None
                full_address = None
                
                # 도로명 주소에서 정보 추출
                if road_address:
                    district = road_address.get('region_2depth_name', '').replace('구', '') + '구'
                    dong = road_address.get('region_3depth_name', '') or road_address.get('region_4depth_name', '')
                    full_address = road_address.get('address_name', '')
                    result['road_address'] = road_address.get('address_name', '')
                
                # 지번 주소에서 추가/보완 정보 추출
                if address:
                    if not district:
                        district = address.get('region_2depth_name', '').replace('구', '') + '구'
                    if not dong:
                        dong = address.get('region_3depth_name', '') or address.get('region_4depth_name', '')
                    if not full_address:
                        full_address = address.get('address_name', '')
                
                result['district'] = district
                result['dong'] = dong  
                result['full_address'] = full_address
                
                # 동명 후처리 (행정동명 정리)
                if result['dong']:
                    result['dong'] = self._normalize_dong_name(result['dong'])
                
                return result
            
            return None
            
        except requests.exceptions.RequestException as e:
            # API 오류시 요청 카운트는 증가시키지 않음
            if response.status_code == 429:  # Too Many Requests
                logger.warning("Rate limit exceeded, backing off")
                time.sleep(1)  # 1초 대기
            logger.error(f"Kakao API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None
    
    def _wait_for_rate_limit(self):
        """API 호출 제한 적용"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _can_make_request(self) -> bool:
        """API 요청 가능 여부 확인"""
        return self.daily_request_count < self.daily_limit
    
    def get_remaining_requests(self) -> int:
        """남은 요청 수 반환"""
        return max(0, self.daily_limit - self.daily_request_count)
    
    def _normalize_dong_name(self, dong_name: str) -> str:
        """동명 정규화"""
        if not dong_name:
            return dong_name
        
        # 특수 케이스 처리
        dong_name = dong_name.strip()
        
        # '동'이 없으면 추가
        if not dong_name.endswith('동'):
            dong_name += '동'
        
        return dong_name
    
    def batch_coordinate_to_address(self, coordinates: list, batch_size: int = 1000, save_progress: bool = True) -> list:
        """
        좌표 리스트를 일괄 변환 (안전한 배치 처리)
        
        Args:
            coordinates: [(lat, lon), ...] 형태의 좌표 리스트
            batch_size: 배치 크기 (중간 저장 단위)
            save_progress: 진행상황 저장 여부
            
        Returns:
            변환 결과 리스트
        """
        results = []
        total = len(coordinates)
        
        logger.info(f"Starting batch geocoding for {total} coordinates")
        logger.info(f"Daily API limit: {self.daily_limit}, remaining: {self.get_remaining_requests()}")
        
        if total > self.get_remaining_requests():
            logger.warning(f"Not enough API requests remaining. Need {total}, have {self.get_remaining_requests()}")
            # 일부만 처리하거나 오류 반환
        
        start_time = time.time()
        
        for i, (lat, lon) in enumerate(coordinates):
            # 주기적 진행상황 로그
            if i % 100 == 0 and i > 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (total - i) / rate if rate > 0 else 0
                logger.info(f"Processed {i}/{total} coordinates ({i/total*100:.1f}%), "
                          f"Rate: {rate:.1f}/sec, ETA: {eta/60:.1f}min, "
                          f"Remaining requests: {self.get_remaining_requests()}")
            
            # API 제한 확인
            if not self._can_make_request():
                logger.error(f"Daily API limit reached at {i}/{total}")
                break
            
            result = self.coordinate_to_address(lat, lon)
            results.append(result)
            
            # 배치 단위로 중간 저장 (선택적)
            if save_progress and i > 0 and i % batch_size == 0:
                logger.info(f"Batch {i//batch_size} completed, saving progress...")
        
        elapsed = time.time() - start_time
        logger.info(f"Batch geocoding completed: {len(results)}/{total} coordinates processed in {elapsed/60:.1f}min")
        logger.info(f"API requests used: {self.daily_request_count}, remaining: {self.get_remaining_requests()}")
        
        return results


class EnhancedAddressParser:
    """주소 파싱 + 지오코딩 결합 클래스"""
    
    def __init__(self):
        from utils.address_parser import SeoulAddressParser
        self.address_parser = SeoulAddressParser()
        self.geocoder = KakaoGeocoder()
    
    def parse_with_coordinates(self, address: str, latitude: float = None, longitude: float = None) -> Dict[str, Any]:
        """
        주소 파싱 + 좌표 기반 지오코딩 결합
        
        Args:
            address: 주소 문자열
            latitude: 위도 (선택)
            longitude: 경도 (선택)
            
        Returns:
            통합 파싱 결과
        """
        result = {
            'original_address': address,
            'district': None,
            'dong': None,
            'cleaned_address': address,
            'parsing_success': False,
            'confidence': 0.0,
            'method': None  # 'address', 'coordinate', 'combined'
        }
        
        # 1. 주소 파싱 먼저 시도
        address_result = self.address_parser.parse_full_address(address)
        
        if address_result['parsing_success'] and address_result['dong']:
            # 주소 파싱 성공
            result.update(address_result)
            result['method'] = 'address'
            return result
        
        # 2. 좌표가 있으면 지오코딩 시도
        if latitude and longitude:
            geo_result = self.geocoder.coordinate_to_address(latitude, longitude)
            
            if geo_result and geo_result['dong']:
                # 지오코딩 성공
                result['district'] = geo_result['district']
                result['dong'] = geo_result['dong']
                result['cleaned_address'] = address_result.get('cleaned_address', address)
                result['parsing_success'] = True
                result['confidence'] = 0.7  # 좌표 기반이므로 높은 신뢰도
                result['method'] = 'coordinate'
                return result
        
        # 3. 둘 다 실패하면 주소 파싱 결과라도 반환
        if address_result['district']:
            result.update(address_result)
            result['method'] = 'address_partial'
        
        return result


def main():
    """지오코딩 테스트"""
    print("=== 카카오 지오코딩 테스트 ===\n")
    
    geocoder = KakaoGeocoder()
    
    # 테스트 좌표들 (서울 주요 지점)
    test_coordinates = [
        (37.5665, 126.9780),  # 서울시청
        (37.5048, 127.0438),  # 강남역 근처
        (37.5511, 126.9882),  # 종로구 
        (37.4979, 127.0276),  # 서초구
        (37.5326, 127.1244),  # 강동구
    ]
    
    print("1. 좌표 → 주소 변환 테스트:")
    for i, (lat, lon) in enumerate(test_coordinates, 1):
        result = geocoder.coordinate_to_address(lat, lon)
        
        print(f"   {i}. 좌표: ({lat}, {lon})")
        if result:
            print(f"      자치구: {result['district']}")
            print(f"      동명: {result['dong']}")
            print(f"      전체주소: {result['full_address']}")
        else:
            print("      변환 실패")
        print()
    
    # 통합 파서 테스트
    print("2. 통합 주소 파싱 테스트:")
    enhanced_parser = EnhancedAddressParser()
    
    test_cases = [
        ("DF013 4-4S 신림동1641-40", 37.4842, 126.9292),
        ("상봉1동 3-4", None, None),
        ("강남구 테헤란로 212", 37.5048, 127.0438),
    ]
    
    for address, lat, lon in test_cases:
        result = enhanced_parser.parse_with_coordinates(address, lat, lon)
        
        print(f"   주소: {address}")
        print(f"   좌표: ({lat}, {lon})")
        print(f"   자치구: {result['district']}")
        print(f"   동명: {result['dong']}")
        print(f"   방법: {result['method']}")
        print(f"   성공: {result['parsing_success']} (신뢰도: {result['confidence']:.2f})")
        print()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
공공데이터포털(data.go.kr) API 클라이언트

공공데이터포털에서 제공하는 다양한 API 서비스에 대한 통합 클라이언트입니다.
"""

import requests
import json
import logging
import time
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import urllib3

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 환경변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class DataGoKrAPI:
    """공공데이터포털 API 클라이언트"""
    
    def __init__(self):
        """API 클라이언트 초기화"""
        self.base_url = "https://apis.data.go.kr"
        self.api_key = os.getenv('SEXUAL_OFFENDER_API_KEY')
        
        if not self.api_key:
            raise ValueError("SEXUAL_OFFENDER_API_KEY not found in environment variables")
        
        # 요청 세션 설정
        self.session = requests.Session()
        self.session.verify = False  # SSL 검증 비활성화
        
        # 요청 헤더 설정
        self.session.headers.update({
            'User-Agent': 'Seoul-Safety-Data-Pipeline/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        # API 제한 설정
        self.request_delay = 0.1  # 요청 간 지연 시간
        self.timeout = 30  # 요청 타임아웃
        self.max_retries = 3  # 최대 재시도 횟수
        
        logger.info("DataGoKrAPI client initialized")
    
    def fetch_data(self, service_path: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        API 데이터 조회
        
        Args:
            service_path: API 서비스 경로 (예: "1383000/sais/SexualAbuseNoticeHouseNumAddrServiceV2/getSexualAbuseNoticeHouseNumAddrListV2")
            params: 요청 파라미터
            
        Returns:
            API 응답 데이터 또는 None
        """
        # URL 구성
        url = f"{self.base_url}/{service_path}"
        
        # 기본 파라미터에 API 키 추가
        request_params = {
            'serviceKey': self.api_key,
            **params
        }
        
        # 재시도 로직
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Fetching {service_path}: attempt {attempt + 1}")
                
                # API 요청
                response = self.session.get(
                    url,
                    params=request_params,
                    timeout=self.timeout
                )
                
                logger.debug(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    # JSON 응답 파싱
                    if 'json' in response.headers.get('content-type', ''):
                        try:
                            data = response.json()
                            return data
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error: {e}")
                            logger.debug(f"Response text: {response.text[:500]}")
                            return None
                    else:
                        # XML 응답 또는 기타 형식
                        logger.debug(f"Non-JSON response: {response.text[:200]}")
                        
                        # XML에서 에러 메시지 확인
                        if 'SERVICE_KEY_IS_NOT_REGISTERED_ERROR' in response.text:
                            logger.error("API key is not registered for this service")
                            return None
                        elif 'SERVICE ERROR' in response.text:
                            logger.error(f"Service error: {response.text}")
                            return None
                        else:
                            # JSON 파싱 시도
                            try:
                                data = response.json()
                                return data
                            except:
                                logger.error(f"Unable to parse response: {response.text[:200]}")
                                return None
                
                elif response.status_code == 429:
                    # Rate limit exceeded
                    logger.warning("Rate limit exceeded, waiting...")
                    time.sleep(5 * (attempt + 1))
                    continue
                    
                else:
                    logger.error(f"HTTP error {response.status_code}: {response.text[:200]}")
                    
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # 지수 백오프
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return None
                        
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    logger.error("Max retries exceeded due to timeout")
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    logger.error("Max retries exceeded due to connection error")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return None
        
        # 요청 간 지연
        time.sleep(self.request_delay)
        return None
    
    def test_connection(self) -> bool:
        """API 연결 테스트"""
        try:
            logger.info("Testing data.go.kr API connection...")
            
            # 성범죄자 주소 API 테스트
            test_params = {
                'pageNo': '1',
                'numOfRows': '1',
                'type': 'json'
            }
            
            service_path = "1383000/sais/SexualAbuseNoticeHouseNumAddrServiceV2/getSexualAbuseNoticeHouseNumAddrListV2"
            response = self.fetch_data(service_path, test_params)
            
            if response:
                if 'response' in response:
                    header = response['response'].get('header', {})
                    if header.get('resultCode') == '0':
                        logger.info("✅ API connection test successful")
                        return True
                    else:
                        logger.error(f"API test failed: {header.get('resultMsg')}")
                        return False
                else:
                    logger.error("Invalid API response format")
                    return False
            else:
                logger.error("API connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"API connection test error: {e}")
            return False
    
    def get_service_info(self, service_path: str) -> Dict[str, Any]:
        """서비스 정보 조회"""
        try:
            # 기본 정보 조회 (첫 페이지)
            params = {
                'pageNo': '1',
                'numOfRows': '1',
                'type': 'json'
            }
            
            response = self.fetch_data(service_path, params)
            
            if response and 'response' in response:
                body = response['response'].get('body', {})
                return {
                    'total_count': body.get('totalCount', 0),
                    'service_available': True,
                    'last_check': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                return {
                    'total_count': 0,
                    'service_available': False,
                    'last_check': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except Exception as e:
            logger.error(f"Error getting service info: {e}")
            return {
                'total_count': 0,
                'service_available': False,
                'error': str(e),
                'last_check': time.strftime('%Y-%m-%d %H:%M:%S')
            }


def main():
    """테스트 실행"""
    print("🌐 Data.go.kr API Client Test")
    print("=" * 40)
    
    try:
        # API 클라이언트 초기화
        api = DataGoKrAPI()
        
        # 연결 테스트
        if api.test_connection():
            print("✅ API connection successful!")
            
            # 서비스 정보 조회
            service_path = "1383000/sais/SexualAbuseNoticeHouseNumAddrServiceV2/getSexualAbuseNoticeHouseNumAddrListV2"
            service_info = api.get_service_info(service_path)
            
            print(f"\n📊 Service Information:")
            print(f"   Total records: {service_info.get('total_count', 0):,}")
            print(f"   Service available: {service_info.get('service_available', False)}")
            print(f"   Last check: {service_info.get('last_check', 'N/A')}")
            
        else:
            print("❌ API connection failed!")
            
    except Exception as e:
        print(f"❌ Test error: {e}")


if __name__ == "__main__":
    main()
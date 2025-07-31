"""
API Configuration Loader

이 모듈은 .env 환경변수 파일을 통해 API 키를 관리합니다.
"""

import os
from typing import Dict, Optional
import logging

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    logging.warning("python-dotenv not installed. Please install with: pip install python-dotenv")

logger = logging.getLogger(__name__)


class APIConfigLoader:
    """API 설정 및 키 관리 클래스 (.env 기반)"""
    
    def __init__(self, env_path: Optional[str] = None):
        """
        API 설정 로더 초기화
        
        Args:
            env_path: .env 파일 경로 (기본값: 자동 탐지)
        """
        self.env_path = env_path
        self.api_services = {
            'kakao': {
                'env_var': 'KAKAO_API_KEY',
                'service_name': '카카오 개발자센터 - Local API',
                'description': '주소를 위도/경도 좌표로 변환하는 지오코딩 서비스',
                'required': True
            },
            'seoul_open_data': {
                'env_var': 'SEOUL_OPEN_API_KEY',
                'service_name': '서울 열린데이터광장',
                'description': '서울시 공공데이터 - 경찰서, 안전시설, CCTV 등',
                'required': True
            },
            'safemap': {
                'env_var': 'SAFEMAP_API_KEY',
                'service_name': '생활안전지도',
                'description': '치안센터, 범죄통계, 안전시설 정보',
                'required': False
            },
            'women_safety': {
                'env_var': 'WOMEN_SAFETY_API_KEY',
                'service_name': '여성안전 API',
                'description': '여성 안전 관련 시설 및 서비스 정보',
                'required': False
            },
            'sexual_offender': {
                'env_var': 'SEXUAL_OFFENDER_API_KEY',
                'service_name': '성범죄자 알림 서비스',
                'description': '성범죄자 거주지 및 위험도 정보',
                'required': False,
                'sensitive': True
            },
            'seoul_streetlight': {
                'env_var': 'SEOUL_STREETLIGHT_API_KEY',
                'service_name': '서울 가로등 정보',
                'description': '서울시 가로등 설치 현황 및 조도 정보',
                'required': False
            }
        }
        
        # .env 파일 로드
        self._load_env_file()
    
    def _load_env_file(self):
        """환경변수 파일을 로드합니다."""
        if DOTENV_AVAILABLE:
            try:
                if self.env_path:
                    load_dotenv(self.env_path)
                else:
                    load_dotenv()  # 현재 디렉토리에서 .env 파일 자동 탐지
                logger.debug("Loaded .env file")
            except Exception as e:
                logger.warning(f"Could not load .env file: {e}")
        else:
            logger.warning("python-dotenv not available. Using system environment variables only.")
    
    def get_api_key(self, service: str) -> Optional[str]:
        """
        특정 서비스의 API 키를 가져옵니다.
        
        Args:
            service: 서비스 이름 (kakao, seoul_open_data, safemap, etc.)
            
        Returns:
            API 키 문자열 또는 None
        """
        if service not in self.api_services:
            logger.warning(f"Unknown service: {service}")
            return None
        
        env_var = self.api_services[service]['env_var']
        api_key = os.getenv(env_var)
        
        if not api_key:
            service_name = self.api_services[service]['service_name']
            logger.warning(f"API key not found for {service_name} (환경변수: {env_var})")
        
        return api_key
    
    def get_all_api_keys(self) -> Dict[str, str]:
        """
        사용 가능한 모든 API 키를 딕셔너리로 반환합니다.
        
        Returns:
            서비스명: API키 매핑 딕셔너리
        """
        keys = {}
        
        for service_name in self.api_services.keys():
            api_key = self.get_api_key(service_name)
            if api_key:
                keys[service_name] = api_key
        
        return keys
    
    def get_service_info(self, service: str) -> Dict[str, str]:
        """
        서비스 정보를 가져옵니다.
        
        Args:
            service: 서비스 이름
            
        Returns:
            서비스 정보 딕셔너리
        """
        return self.api_services.get(service, {})
    
    def is_service_required(self, service: str) -> bool:
        """서비스가 필수인지 확인합니다."""
        service_info = self.get_service_info(service)
        return service_info.get('required', False)
    
    def validate_required_keys(self) -> Dict[str, bool]:
        """
        필수 API 키가 모두 설정되어 있는지 확인합니다.
        
        Returns:
            서비스명: 유효성 검사 결과 매핑
        """
        validation_results = {}
        
        for service_name, service_config in self.api_services.items():
            is_required = service_config.get('required', False)
            has_key = self.get_api_key(service_name) is not None
            
            validation_results[service_name] = {
                'required': is_required,
                'has_key': has_key,
                'valid': has_key if is_required else True
            }
        
        return validation_results
    
    def print_service_info(self, service: Optional[str] = None):
        """서비스 정보를 출력합니다."""
        if service:
            # 특정 서비스 정보 출력
            service_info = self.get_service_info(service)
            if not service_info:
                print(f"서비스 '{service}'를 찾을 수 없습니다.")
                return
            
            print(f"\n=== {service_info.get('service_name', service)} ===")
            print(f"환경변수: {service_info.get('env_var', 'N/A')}")
            print(f"설명: {service_info.get('description', 'N/A')}")
            print(f"필수: {'예' if service_info.get('required') else '아니오'}")
            if service_info.get('sensitive'):
                print("⚠️  민감정보: 사용 시 주의 필요")
            
            # API 키 상태
            has_key = self.get_api_key(service) is not None
            print(f"API 키 설정됨: {'예' if has_key else '아니오'}")
            
        else:
            # 모든 서비스 정보 출력
            print("\n=== 사용 가능한 API 서비스 ===")
            
            for service_name, service_info in self.api_services.items():
                has_key = self.get_api_key(service_name) is not None
                status = "✓" if has_key else "✗"
                required = "필수" if service_info.get('required') else "선택"
                sensitive = " ⚠️" if service_info.get('sensitive') else ""
                
                print(f"{status} {service_info.get('service_name', service_name)} ({required}){sensitive}")
                print(f"    환경변수: {service_info.get('env_var')}")
    
    def create_legacy_variables(self) -> Dict[str, str]:
        """
        기존 코드와의 호환성을 위해 레거시 변수명으로 API 키를 반환합니다.
        
        Returns:
            레거시 변수명: API키 매핑 딕셔너리
        """
        legacy_mapping = {
            'kakao_key': self.get_api_key('kakao'),
            'cctv_key': self.get_api_key('seoul_open_data'),
            'safe_map_key': self.get_api_key('safemap'),
            'female_safety_key': self.get_api_key('women_safety'),
            'sexual_offender_key': self.get_api_key('sexual_offender'),
            'streetlight_key': self.get_api_key('seoul_streetlight')
        }
        
        # None 값 제거
        return {k: v for k, v in legacy_mapping.items() if v is not None}


# 편의 함수들
def load_api_config(env_path: Optional[str] = None) -> APIConfigLoader:
    """API 설정 로더를 생성하고 반환합니다."""
    return APIConfigLoader(env_path)


def get_api_key(service: str, env_path: Optional[str] = None) -> Optional[str]:
    """특정 서비스의 API 키를 빠르게 가져옵니다."""
    loader = APIConfigLoader(env_path)
    return loader.get_api_key(service)


def get_legacy_keys(env_path: Optional[str] = None) -> Dict[str, str]:
    """기존 코드 호환을 위한 레거시 키 변수들을 반환합니다."""
    loader = APIConfigLoader(env_path)
    return loader.create_legacy_variables()


# 직접 환경변수 접근 함수들 (간단한 사용을 위해)
def get_kakao_key() -> Optional[str]:
    """카카오 API 키를 가져옵니다."""
    return os.getenv('KAKAO_API_KEY')


def get_seoul_open_data_key() -> Optional[str]:
    """서울 열린데이터 API 키를 가져옵니다."""
    return os.getenv('SEOUL_OPEN_API_KEY')


def get_safemap_key() -> Optional[str]:
    """생활안전지도 API 키를 가져옵니다."""
    return os.getenv('SAFEMAP_API_KEY')


def get_women_safety_key() -> Optional[str]:
    """여성안전 API 키를 가져옵니다."""
    return os.getenv('WOMEN_SAFETY_API_KEY')


def get_sexual_offender_key() -> Optional[str]:
    """성범죄자 알림 API 키를 가져옵니다."""
    return os.getenv('SEXUAL_OFFENDER_API_KEY')


def get_seoul_streetlight_key() -> Optional[str]:
    """서울 가로등 API 키를 가져옵니다."""
    return os.getenv('SEOUL_STREETLIGHT_API_KEY')


def main():
    """설정 로더 테스트 및 정보 출력"""
    loader = APIConfigLoader()
    
    print("=== API 설정 로더 테스트 (.env 기반) ===")
    
    # 모든 서비스 정보 출력
    loader.print_service_info()
    
    # 필수 키 검증
    print("\n=== 필수 API 키 검증 ===")
    validation = loader.validate_required_keys()
    
    all_required_valid = True
    for service, result in validation.items():
        if result['required']:
            status = "✓" if result['valid'] else "✗"
            print(f"{status} {service}: {'설정됨' if result['has_key'] else '누락'}")
            if not result['valid']:
                all_required_valid = False
    
    if all_required_valid:
        print("\n✅ 모든 필수 API 키가 설정되었습니다!")
    else:
        print("\n❌ 일부 필수 API 키가 누락되었습니다.")
        print("   .env 파일에 누락된 API 키를 추가해주세요.")
    
    # 레거시 변수 출력
    print("\n=== 레거시 호환 변수 ===")
    legacy_keys = loader.create_legacy_variables()
    for var_name, api_key in legacy_keys.items():
        masked_key = api_key[:8] + "..." if len(api_key) > 8 else api_key
        print(f"{var_name}: {masked_key}")


if __name__ == "__main__":
    main()
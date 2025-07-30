"""
Settings and Configuration Management

환경변수와 애플리케이션 설정을 관리하는 모듈
"""

import os
from typing import Optional
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logging.warning("python-dotenv not installed. Using system environment variables only.")


class Settings:
    """애플리케이션 설정 관리 클래스"""
    
    # API Keys
    KAKAO_API_KEY: str = os.getenv('KAKAO_API_KEY', '')
    SEOUL_OPEN_API_KEY: str = os.getenv('SEOUL_OPEN_API_KEY', '')
    SAFEMAP_API_KEY: str = os.getenv('SAFEMAP_API_KEY', '')
    WOMEN_SAFETY_API_KEY: str = os.getenv('WOMEN_SAFETY_API_KEY', '')
    SEXUAL_OFFENDER_API_KEY: str = os.getenv('SEXUAL_OFFENDER_API_KEY', '')
    SEOUL_STREETLIGHT_API_KEY: str = os.getenv('SEOUL_STREETLIGHT_API_KEY', '')
    
    # Database Configuration
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: int = int(os.getenv('DB_PORT', '5432'))
    DB_NAME: str = os.getenv('DB_NAME', 'seoul_safety')
    DB_USER: str = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')
    
    # API Configuration
    API_REQUEST_DELAY: float = float(os.getenv('API_REQUEST_DELAY', '0.2'))
    API_TIMEOUT: int = int(os.getenv('API_TIMEOUT', '30'))
    API_MAX_RETRIES: int = int(os.getenv('API_MAX_RETRIES', '3'))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Data Processing Configuration
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '1000'))
    CACHE_DIR: str = os.getenv('CACHE_DIR', 'data/cache')
    
    # Seoul Open Data API Endpoints
    SEOUL_API_BASE_URL: str = "http://openapi.seoul.go.kr:8088"
    
    # CCTV API Configuration
    CCTV_API_SERVICE: str = "ListCctvInformationService"  # 실제 서비스명으로 변경 필요
    
    @classmethod
    def get_database_url(cls) -> str:
        """PostgreSQL 연결 URL 생성"""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def get_seoul_api_url(cls, service_name: str, start_idx: int = 1, end_idx: int = 1000) -> str:
        """서울 열린데이터 API URL 생성"""
        return f"{cls.SEOUL_API_BASE_URL}/{cls.SEOUL_OPEN_API_KEY}/json/{service_name}/{start_idx}/{end_idx}/"
    
    @classmethod
    def validate_required_settings(cls) -> dict:
        """필수 설정 값들이 설정되어 있는지 확인"""
        required_settings = {
            'SEOUL_OPEN_API_KEY': cls.SEOUL_OPEN_API_KEY,
            'DB_PASSWORD': cls.DB_PASSWORD,
        }
        
        validation_results = {}
        for setting_name, setting_value in required_settings.items():
            validation_results[setting_name] = {
                'is_set': bool(setting_value),
                'value_preview': setting_value[:8] + '...' if len(setting_value) > 8 else setting_value
            }
        
        return validation_results
    
    @classmethod
    def setup_logging(cls):
        """로깅 설정"""
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO),
            format=cls.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('seoul_safety_pipeline.log', encoding='utf-8')
            ]
        )


# 설정 인스턴스 생성
settings = Settings()

# 로깅 설정 초기화
settings.setup_logging()


def main():
    """설정 테스트 및 확인"""
    print("=== Seoul Safety Data Pipeline 설정 확인 ===\n")
    
    # API 키 확인
    print("API 키 설정 상태:")
    api_keys = {
        'KAKAO_API_KEY': settings.KAKAO_API_KEY,
        'SEOUL_OPEN_API_KEY': settings.SEOUL_OPEN_API_KEY,
        'SAFEMAP_API_KEY': settings.SAFEMAP_API_KEY,
        'WOMEN_SAFETY_API_KEY': settings.WOMEN_SAFETY_API_KEY,
        'SEXUAL_OFFENDER_API_KEY': settings.SEXUAL_OFFENDER_API_KEY,
        'SEOUL_STREETLIGHT_API_KEY': settings.SEOUL_STREETLIGHT_API_KEY,
    }
    
    for key_name, key_value in api_keys.items():
        status = "✓" if key_value else "✗"
        preview = key_value[:8] + "..." if len(key_value) > 8 else key_value
        print(f"  {status} {key_name}: {preview}")
    
    # 데이터베이스 설정 확인
    print(f"\n데이터베이스 설정:")
    print(f"  Host: {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"  Database: {settings.DB_NAME}")
    print(f"  User: {settings.DB_USER}")
    db_password_status = "✓" if settings.DB_PASSWORD else "✗"
    print(f"  Password: {db_password_status}")
    
    # API 설정 확인
    print(f"\nAPI 설정:")
    print(f"  Request Delay: {settings.API_REQUEST_DELAY}초")
    print(f"  Timeout: {settings.API_TIMEOUT}초")
    print(f"  Max Retries: {settings.API_MAX_RETRIES}회")
    
    # 필수 설정 검증
    print(f"\n필수 설정 검증:")
    validation = settings.validate_required_settings()
    all_valid = True
    
    for setting_name, result in validation.items():
        status = "✓" if result['is_set'] else "✗"
        print(f"  {status} {setting_name}: {'설정됨' if result['is_set'] else '누락'}")
        if not result['is_set']:
            all_valid = False
    
    if all_valid:
        print(f"\n✅ 모든 필수 설정이 완료되었습니다!")
    else:
        print(f"\n❌ 일부 필수 설정이 누락되었습니다. .env 파일을 확인해주세요.")
    
    # 샘플 API URL 생성
    print(f"\n샘플 API URL:")
    sample_url = settings.get_seoul_api_url("ListCctvInformationService", 1, 100)
    print(f"  CCTV API: {sample_url}")


if __name__ == "__main__":
    main()
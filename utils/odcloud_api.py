"""
공공데이터포털 OpenAPI 클라이언트 (api.odcloud.kr)

페이지네이션 기반 JSON API 처리 - 범용 클라이언트
"""

import requests
import logging
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ODCloudAPIClient:
    """공공데이터포털 OpenAPI 범용 클라이언트"""
    
    def __init__(self):
        self.base_url = "https://api.odcloud.kr/api"
        self.session = requests.Session()
        
        # API 호출 제한 (초당 최대 5회)
        self.last_request_time = 0
        self.min_interval = 0.2  # 200ms
        
    def _wait_for_rate_limit(self):
        """API 호출 제한 적용"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def fetch_page(self, service_id: str, api_key: str, page: int = 1, per_page: int = 1000, 
                   return_type: str = "JSON") -> Optional[Dict[str, Any]]:
        """
        단일 페이지 데이터 가져오기
        
        Args:
            service_id: 서비스 ID (예: "uddi:20b10130-21ed-43f3-8e58-b8692fb8a2ff")
            api_key: API 키
            page: 페이지 번호 (1부터 시작)
            per_page: 페이지당 결과 수
            return_type: 응답 타입 (JSON 또는 XML)
            
        Returns:
            API 응답 데이터 또는 None
        """
        try:
            self._wait_for_rate_limit()
            
            url = f"{self.base_url}/{service_id}"
            params = {
                'page': page,
                'perPage': per_page,
                'returnType': return_type,
                'serviceKey': api_key
            }
            
            logger.debug(f"Fetching {service_id}: page {page} (per_page: {per_page})")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            if return_type.upper() == "JSON":
                data = response.json()
                return data
            else:
                # XML 처리는 나중에 필요시 구현
                return {"data": []}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {service_id} page {page}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {service_id} page {page}: {e}")
            return None
    
    def fetch_all_pages(self, service_id: str, api_key: str, max_pages: int = None, 
                        per_page: int = 1000) -> List[Dict[str, Any]]:
        """
        모든 페이지 데이터 가져오기
        
        Args:
            service_id: 서비스 ID
            api_key: API 키  
            max_pages: 최대 페이지 수 (무한 루프 방지)
            per_page: 페이지당 결과 수
            
        Returns:
            전체 데이터 리스트
        """
        all_data = []
        page = 1
        
        logger.info(f"Starting to fetch all pages for {service_id}")
        
        while page <= max_pages:
            response = self.fetch_page(service_id, api_key, page, per_page)
            
            if not response:
                logger.warning(f"Failed to fetch page {page}, stopping")
                break
            
            # 응답 구조 확인
            data_list = response.get('data', [])
            current_count = response.get('currentCount', 0)
            total_count = response.get('totalCount', 0)
            
            if not data_list:
                logger.info(f"No more data on page {page}, stopping")
                break
            
            all_data.extend(data_list)
            
            logger.info(f"Fetched page {page}: {current_count} records (total so far: {len(all_data)}/{total_count})")
            
            # 더 이상 데이터가 없으면 중단
            if current_count < per_page or len(all_data) >= total_count:
                logger.info(f"Reached end of data. Total records: {len(all_data)}")
                break
            
            page += 1
        
        logger.info(f"Completed fetching {service_id}: {len(all_data)} total records")
        return all_data
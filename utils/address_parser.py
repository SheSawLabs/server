"""
범용 주소 파싱 유틸리티

서울시 공공데이터의 주소에서 자치구, 동명을 추출하고 정규화하는 기능
CCTV, 안전시설, 가로등 등 모든 데이터에서 공통으로 사용 가능
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
import sys
import os

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


class SeoulAddressParser:
    """서울시 주소 파싱 클래스"""
    
    def __init__(self):
        # 서울시 25개 자치구
        self.seoul_districts = {
            '종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구',
            '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구',
            '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구',
            '서초구', '강남구', '송파구', '강동구'
        }
        
        # 동명 추출 패턴들 (우선순위 순)
        self.dong_patterns = [
            r'([가-힣]+\d*동)\s+\d',           # 상봉1동 123-45 형태
            r'([가-힣]+\d*동)\s',             # 상봉1동 (공백 후)
            r'^([가-힣]+\d*동)',              # 문장 시작의 동명
            r'([가-힣]+동)\s+\d',             # 명동 123-45 형태  
            r'([가-힣]+동)\s',                # 명동 (공백 후)
            r'^([가-힣]+동)',                 # 문장 시작의 동명
            r'서울특별시\s+[가-힣]+구\s+([가-힣]+\d*동)',  # 전체 주소에서 동명
            r'서울시\s+[가-힣]+구\s+([가-힣]+\d*동)',     # 축약 주소에서 동명
        ]
        
        # 자치구 추출 패턴들
        self.district_patterns = [
            r'서울특별시\s+([가-힣]+구)',      # 서울특별시 강남구
            r'서울시\s+([가-힣]+구)',         # 서울시 강남구
            r'^([가-힣]+구)',                # 강남구 (문장 시작)
            r'([가-힣]+구)\s',               # 강남구 (공백 후)
        ]
        
        # 특수 지역 매핑 (랜드마크 → 동명)
        self.landmark_to_dong = {
            '청와대': '청운효자동',
            '국회의사당': '여의동', 
            '서울역': '동자동',
            '강남역': '역삼동',
            '홍대입구': '서교동',
            '이태원': '이태원동',
            '명동': '명동',
            '종로': '종로1가동',
            '시청': '소공동',
            '동대문': '동대문로동',
            '남대문시장': '남대문로동',
            '경복궁': '세종로동',
            '덕수궁': '정동',
            '창덕궁': '와룡동',
        }
        
        # 자치구별 대표 동명 매핑 (동이 추출되지 않을 경우 대체)
        self.district_default_dong = {
            '중구': '명동',
            '종로구': '종로1가동', 
            '용산구': '이태원동',
            '강남구': '역삼동',
            '서초구': '서초동',
            '송파구': '잠실동',
            '강동구': '천호동',
        }
        
        # 유효하지 않은 동명들
        self.invalid_dong_names = {
            '서울시', '서울특별시', '서울', '시청', '구청', '동사무소', '출장소',
            '지하철', '역', '터미널', '공원', '학교', '병원', '아파트', '빌딩'
        }
    
    def parse_full_address(self, address: str) -> Dict[str, Any]:
        """
        주소를 완전히 파싱하여 자치구, 동, 정리된 주소 반환
        
        Args:
            address: 원본 주소 문자열
            
        Returns:
            파싱 결과 딕셔너리
        """
        result = {
            'original_address': address,
            'district': None,
            'dong': None, 
            'cleaned_address': address,
            'parsing_success': False,
            'confidence': 0.0  # 파싱 신뢰도 (0.0 ~ 1.0)
        }
        
        if not address or not isinstance(address, str):
            return result
        
        address = address.strip()
        confidence_score = 0.0
        
        # 1. 자치구 추출
        district = self.extract_district(address)
        if district:
            result['district'] = district
            confidence_score += 0.3
        
        # 2. 동명 추출
        dong = self.extract_dong(address)
        if dong:
            result['dong'] = dong
            confidence_score += 0.5
        elif district and district in self.district_default_dong:
            # 동이 없으면 자치구 기본 동 사용
            result['dong'] = self.district_default_dong[district]
            confidence_score += 0.2
        
        # 3. 주소 정리
        cleaned = self.clean_address(address)
        result['cleaned_address'] = cleaned
        confidence_score += 0.2
        
        result['confidence'] = min(confidence_score, 1.0)
        result['parsing_success'] = confidence_score >= 0.5
        
        return result
    
    def extract_district(self, address: str) -> Optional[str]:
        """주소에서 자치구명 추출"""
        if not address:
            return None
        
        # 패턴 매칭으로 자치구 추출
        for pattern in self.district_patterns:
            match = re.search(pattern, address)
            if match:
                district = match.group(1)
                if district in self.seoul_districts:
                    return district
        
        # 직접 매칭 (패턴에 안 잡힌 경우)
        for district in self.seoul_districts:
            if district in address:
                return district
        
        return None
    
    def extract_dong(self, address: str) -> Optional[str]:
        """주소에서 동명 추출"""
        if not address:
            return None
        
        # 랜드마크 우선 확인
        for landmark, dong in self.landmark_to_dong.items():
            if landmark in address:
                return dong
        
        # 패턴 매칭으로 동명 추출
        for pattern in self.dong_patterns:
            match = re.search(pattern, address)
            if match:
                dong_name = match.group(1)
                if self._is_valid_dong_name(dong_name):
                    return dong_name
        
        return None
    
    def clean_address(self, address: str) -> str:
        """주소에서 불필요한 부분 제거 및 정리"""
        if not address:
            return address
        
        cleaned = address
        
        # 공통 제거 패턴들
        patterns_to_remove = [
            r'_[A-Z0-9-]+',                # CCTV 코드 (_C-SB01-0021-B)
            r'\([^)]*고정[^)]*\)',          # (고정1), (고정)
            r'\([^)]*설치[^)]*\)',          # (설치1), (설치)
            r'\([^)]*번[^)]*\)',           # (1번), (A번)
            r'[\s]*-[\s]*\d+호',          # -101호, - 205호
            r'[\s]*\d+호',                # 101호
            r'\s+', # 여러 공백을 하나로
        ]
        
        for pattern in patterns_to_remove:
            if pattern == r'\s+':
                cleaned = re.sub(pattern, ' ', cleaned)
            else:
                cleaned = re.sub(pattern, '', cleaned)
        
        return cleaned.strip()
    
    def _is_valid_dong_name(self, dong_name: str) -> bool:
        """동명 유효성 검사"""
        if not dong_name or len(dong_name) < 2:
            return False
        
        if dong_name in self.invalid_dong_names:
            return False
        
        # '동'으로 끝나는지 확인
        if not dong_name.endswith('동'):
            return False
        
        # 한글 + 숫자 + 동 패턴인지 확인
        if not re.match(r'^[가-힣]+\d*동$', dong_name):
            return False
        
        # 너무 긴 동명 제외 (일반적으로 10자 이내)
        if len(dong_name) > 10:
            return False
        
        return True
    
    def batch_parse_addresses(self, addresses: List[str]) -> List[Dict[str, Any]]:
        """주소 리스트를 일괄 파싱"""
        results = []
        for address in addresses:
            result = self.parse_full_address(address)
            results.append(result)
        return results
    
    def get_parsing_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """파싱 결과 통계"""
        total = len(results)
        if total == 0:
            return {}
        
        successful = sum(1 for r in results if r['parsing_success'])
        with_district = sum(1 for r in results if r['district'])
        with_dong = sum(1 for r in results if r['dong'])
        avg_confidence = sum(r['confidence'] for r in results) / total
        
        # 자치구별 통계
        district_counts = {}
        for r in results:
            if r['district']:
                district_counts[r['district']] = district_counts.get(r['district'], 0) + 1
        
        return {
            'total_addresses': total,
            'successful_parsing': successful,
            'success_rate': successful / total * 100,
            'district_extraction_rate': with_district / total * 100,
            'dong_extraction_rate': with_dong / total * 100,
            'average_confidence': avg_confidence,
            'district_distribution': district_counts
        }


def main():
    """주소 파싱 테스트"""
    parser = SeoulAddressParser()
    
    # 다양한 데이터 소스의 샘플 주소들
    sample_addresses = [
        # CCTV 주소들
        "상봉1동 3-4(고정2)_C-SB01-0021-B",
        "면목2동 178-19(고정1)_C-MM02-0019-A",
        
        # 일반 주소들  
        "서울특별시 강남구 역삼동 123-45",
        "서울시 종로구 명동 567-89",
        "중구 명동 12-34",
        "강남구 테헤란로 212",
        
        # 랜드마크 주소들
        "청와대 근처",
        "강남역 2번 출구",
        "서울역 광장",
        
        # 불완전한 주소들
        "강남구 123-45",
        "역삼동",
        "잘못된주소형태",
        None,
        ""
    ]
    
    print("=== 서울시 주소 파싱 테스트 ===\n")
    
    results = []
    for addr in sample_addresses:
        result = parser.parse_full_address(addr)
        results.append(result)
        
        print(f"원본: {addr}")
        print(f"자치구: {result['district']}")
        print(f"동명: {result['dong']}")
        print(f"정리된 주소: {result['cleaned_address']}")
        print(f"성공: {result['parsing_success']} (신뢰도: {result['confidence']:.2f})")
        print("-" * 60)
    
    # 통계 출력
    stats = parser.get_parsing_statistics(results)
    print("\n=== 파싱 통계 ===")
    print(f"전체 주소: {stats['total_addresses']}개")
    print(f"파싱 성공률: {stats['success_rate']:.1f}%")
    print(f"자치구 추출률: {stats['district_extraction_rate']:.1f}%")
    print(f"동명 추출률: {stats['dong_extraction_rate']:.1f}%")
    print(f"평균 신뢰도: {stats['average_confidence']:.2f}")
    
    if stats['district_distribution']:
        print(f"\n자치구별 분포:")
        for district, count in sorted(stats['district_distribution'].items()):
            print(f"  {district}: {count}개")


if __name__ == "__main__":
    main()
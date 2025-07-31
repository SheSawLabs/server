#!/usr/bin/env python3
"""
CPTED 원칙 기반 안전도 계산 모듈

CPTED (Crime Prevention Through Environmental Design) 5개 원칙:
1. 자연적 감시 (Natural Surveillance) - 가중치: 35%
2. 접근통제 (Access Control) - 가중치: 25%  
3. 영역성 강화 (Territoriality) - 가중치: 20%
4. 유지관리 (Maintenance) - 가중치: 10%
5. 활동성 (Activity Support) - 가중치: 10%
"""

import math
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import sys
import os

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_connection import get_db_manager

logger = logging.getLogger(__name__)


@dataclass
class SafetyFactors:
    """안전 요소들을 담는 데이터 클래스"""
    # 자연적 감시 (Natural Surveillance) - 35%
    cctv_count: int = 0
    streetlight_count: int = 0
    
    # 접근통제 (Access Control) - 25%
    sexual_offender_count: int = 0
    
    # 영역성 강화 (Territoriality) - 20%
    police_station_count: int = 0
    female_safety_house_count: int = 0
    
    # 유지관리 (Maintenance) - 10%
    # TODO: 어두운 골목, 쓰레기 방치 등 데이터 필요
    maintenance_score: float = 0.5  # 기본값 (0.0 ~ 1.0)
    
    # 활동성 (Activity Support) - 10%
    delivery_box_count: int = 0
    # TODO: 유동인구, 상권 데이터 필요
    activity_score: float = 0.5  # 기본값 (0.0 ~ 1.0)


@dataclass
class SafetyScore:
    """계산된 안전도 점수"""
    total_score: float
    natural_surveillance: float
    access_control: float
    territoriality: float
    maintenance: float
    activity_support: float
    grade: str
    timestamp: datetime


class CPTEDCalculator:
    """CPTED 원칙 기반 안전도 계산기"""
    
    # CPTED 원칙별 가중치
    WEIGHTS = {
        'natural_surveillance': 0.35,    # 자연적 감시
        'access_control': 0.25,          # 접근통제
        'territoriality': 0.20,          # 영역성 강화
        'maintenance': 0.10,             # 유지관리
        'activity_support': 0.10         # 활동성
    }
    
    # 안전도 등급 기준
    GRADE_THRESHOLDS = {
        'A': 80.0,   # 매우 안전
        'B': 65.0,   # 안전
        'C': 50.0,   # 보통
        'D': 35.0,   # 위험
        'E': 0.0     # 매우 위험
    }
    
    def __init__(self):
        self.db_manager = get_db_manager()
    
    def calculate_natural_surveillance_score(self, factors: SafetyFactors, area_size: float = 1.0) -> float:
        """
        자연적 감시 점수 계산 (CCTV, 가로등)
        
        Args:
            factors: 안전 요소 데이터
            area_size: 지역 크기 (km²) - 정규화용
            
        Returns:
            0-100 점수
        """
        # CCTV 밀도 점수 (개/km²)
        cctv_density = factors.cctv_count / area_size
        cctv_score = min(100, cctv_density * 2)  # CCTV 50개/km²를 100점으로 설정
        
        # 가로등 밀도 점수 (개/km²)
        streetlight_density = factors.streetlight_count / area_size
        streetlight_score = min(100, streetlight_density * 0.1)  # 가로등 1000개/km²를 100점으로 설정
        
        # 가중 평균 (CCTV 70%, 가로등 30%)
        return cctv_score * 0.7 + streetlight_score * 0.3
    
    def calculate_access_control_score(self, factors: SafetyFactors, area_size: float = 1.0) -> float:
        """
        접근통제 점수 계산 (성범죄자 정보 - 역산)
        
        Args:
            factors: 안전 요소 데이터
            area_size: 지역 크기 (km²)
            
        Returns:
            0-100 점수 (성범죄자가 많을수록 낮은 점수)
        """
        # 성범죄자 밀도 (개/km²)
        offender_density = factors.sexual_offender_count / area_size
        
        # 밀도가 높을수록 점수 감소 (지수 감소 함수 사용)
        # 밀도 10개/km²를 50점으로, 0개/km²를 100점으로 설정
        if offender_density == 0:
            return 100.0
        else:
            score = 100 * math.exp(-offender_density / 10)
            return max(0, score)
    
    def calculate_territoriality_score(self, factors: SafetyFactors, area_size: float = 1.0) -> float:
        """
        영역성 강화 점수 계산 (경찰서, 여성안심지킴이집)
        
        Args:
            factors: 안전 요소 데이터
            area_size: 지역 크기 (km²)
            
        Returns:
            0-100 점수
        """
        # 경찰서 밀도 점수
        police_density = factors.police_station_count / area_size
        police_score = min(100, police_density * 20)  # 경찰서 5개/km²를 100점으로 설정
        
        # 여성안심지킴이집 밀도 점수
        safety_house_density = factors.female_safety_house_count / area_size
        safety_house_score = min(100, safety_house_density * 5)  # 20개/km²를 100점으로 설정
        
        # 가중 평균 (경찰서 70%, 여성안심지킴이집 30%)
        return police_score * 0.7 + safety_house_score * 0.3
    
    def calculate_maintenance_score(self, factors: SafetyFactors) -> float:
        """
        유지관리 점수 계산
        
        Args:
            factors: 안전 요소 데이터
            
        Returns:
            0-100 점수
        """
        # 현재는 기본값 사용
        # TODO: 실제 유지관리 데이터 (어두운 골목, 쓰레기 방치 등) 연동
        return factors.maintenance_score * 100
    
    def calculate_activity_support_score(self, factors: SafetyFactors, area_size: float = 1.0) -> float:
        """
        활동성 점수 계산 (안심택배함, 유동인구 등)
        
        Args:
            factors: 안전 요소 데이터
            area_size: 지역 크기 (km²)
            
        Returns:
            0-100 점수
        """
        # 안심택배함 밀도 점수
        delivery_density = factors.delivery_box_count / area_size
        delivery_score = min(100, delivery_density * 10)  # 10개/km²를 100점으로 설정
        
        # 기본 활동성 점수와 가중 평균
        activity_base_score = factors.activity_score * 100
        
        return delivery_score * 0.3 + activity_base_score * 0.7
    
    def calculate_safety_score(self, factors: SafetyFactors, area_size: float = 1.0) -> SafetyScore:
        """
        종합 안전도 점수 계산
        
        Args:
            factors: 안전 요소 데이터
            area_size: 지역 크기 (km²)
            
        Returns:
            SafetyScore 객체
        """
        # 각 CPTED 원칙별 점수 계산
        natural_surveillance = self.calculate_natural_surveillance_score(factors, area_size)
        access_control = self.calculate_access_control_score(factors, area_size)
        territoriality = self.calculate_territoriality_score(factors, area_size)
        maintenance = self.calculate_maintenance_score(factors)
        activity_support = self.calculate_activity_support_score(factors, area_size)
        
        # 가중치 적용하여 종합 점수 계산
        total_score = (
            natural_surveillance * self.WEIGHTS['natural_surveillance'] +
            access_control * self.WEIGHTS['access_control'] +
            territoriality * self.WEIGHTS['territoriality'] +
            maintenance * self.WEIGHTS['maintenance'] +
            activity_support * self.WEIGHTS['activity_support']
        )
        
        # 등급 결정
        grade = self.get_safety_grade(total_score)
        
        return SafetyScore(
            total_score=round(total_score, 2),
            natural_surveillance=round(natural_surveillance, 2),
            access_control=round(access_control, 2),
            territoriality=round(territoriality, 2),
            maintenance=round(maintenance, 2),
            activity_support=round(activity_support, 2),
            grade=grade,
            timestamp=datetime.now()
        )
    
    def get_safety_grade(self, score: float) -> str:
        """안전도 점수를 등급으로 변환"""
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade
        return 'E'
    
    def get_safety_factors_by_dong(self, district: str, dong: str) -> SafetyFactors:
        """
        동별 안전 요소 데이터 조회
        
        Args:
            district: 구명 (예: '강남구')
            dong: 동명 (예: '역삼동')
            
        Returns:
            SafetyFactors 객체
        """
        try:
            # CCTV 개수
            cctv_query = """
                SELECT COUNT(*) as count 
                FROM cctv_installations 
                WHERE district = %s AND dong = %s
            """
            cctv_result = self.db_manager.execute_query(cctv_query, (district, dong))
            cctv_count = cctv_result[0]['count'] if cctv_result else 0
            
            # 가로등 개수  
            streetlight_query = """
                SELECT COUNT(*) as count 
                FROM streetlight_installations 
                WHERE district = %s AND dong = %s
            """
            streetlight_result = self.db_manager.execute_query(streetlight_query, (district, dong))
            streetlight_count = streetlight_result[0]['count'] if streetlight_result else 0
            
            # 성범죄자 개수
            offender_query = """
                SELECT COUNT(*) as count 
                FROM sexual_offender_addresses 
                WHERE city_county_name = %s AND emd_name = %s
            """
            offender_result = self.db_manager.execute_query(offender_query, (district, dong))
            offender_count = offender_result[0]['count'] if offender_result else 0
            
            # 경찰서 개수
            police_query = """
                SELECT COUNT(*) as count 
                FROM police_stations 
                WHERE district_name = %s AND dong_name = %s
            """
            police_result = self.db_manager.execute_query(police_query, (district, dong))
            police_count = police_result[0]['count'] if police_result else 0
            
            # 여성안심지킴이집 개수
            safety_house_query = """
                SELECT COUNT(*) as count 
                FROM female_safety_houses 
                WHERE district_name = %s AND dong_name = %s
            """
            safety_house_result = self.db_manager.execute_query(safety_house_query, (district, dong))
            safety_house_count = safety_house_result[0]['count'] if safety_house_result else 0
            
            # 안심택배함 개수
            delivery_query = """
                SELECT COUNT(*) as count 
                FROM safe_delivery_boxes 
                WHERE district_name = %s AND dong_name = %s
            """
            delivery_result = self.db_manager.execute_query(delivery_query, (district, dong))
            delivery_count = delivery_result[0]['count'] if delivery_result else 0
            
            return SafetyFactors(
                cctv_count=cctv_count,
                streetlight_count=streetlight_count,
                sexual_offender_count=offender_count,
                police_station_count=police_count,
                female_safety_house_count=safety_house_count,
                delivery_box_count=delivery_count
            )
            
        except Exception as e:
            logger.error(f"Error getting safety factors for {district} {dong}: {e}")
            return SafetyFactors()
    
    def calculate_dong_safety_score(self, district: str, dong: str, area_size: float = 1.0) -> SafetyScore:
        """
        특정 동의 안전도 점수 계산
        
        Args:
            district: 구명
            dong: 동명
            area_size: 동의 면적 (km²)
            
        Returns:
            SafetyScore 객체
        """
        factors = self.get_safety_factors_by_dong(district, dong)
        return self.calculate_safety_score(factors, area_size)


def main():
    """테스트 실행"""
    print("🔒 CPTED 안전도 계산 시스템 테스트")
    print("=" * 50)
    
    calculator = CPTEDCalculator()
    
    # 강남구 역삼동 테스트
    print("\n📍 강남구 역삼동 안전도 분석:")
    safety_score = calculator.calculate_dong_safety_score("강남구", "역삼동", area_size=2.8)
    
    print(f"   종합 안전도: {safety_score.total_score}점 ({safety_score.grade}등급)")
    print(f"   자연적 감시: {safety_score.natural_surveillance}점")
    print(f"   접근통제: {safety_score.access_control}점")
    print(f"   영역성 강화: {safety_score.territoriality}점")
    print(f"   유지관리: {safety_score.maintenance}점")
    print(f"   활동성: {safety_score.activity_support}점")
    
    # 샘플 데이터로 계산 테스트
    print(f"\n🧪 샘플 데이터 테스트:")
    sample_factors = SafetyFactors(
        cctv_count=50,
        streetlight_count=100,
        sexual_offender_count=2,
        police_station_count=3,
        female_safety_house_count=10,
        delivery_box_count=5
    )
    
    sample_score = calculator.calculate_safety_score(sample_factors, area_size=1.0)
    print(f"   종합 안전도: {sample_score.total_score}점 ({sample_score.grade}등급)")


if __name__ == "__main__":
    main()
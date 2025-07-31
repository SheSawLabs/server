#!/usr/bin/env python3
"""
Safety Analyzer - 안전도 분석 메인 클래스
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety_score.cpted_calculator import CPTEDCalculator, SafetyFactors
from db.db_connection import get_db_manager
from collections import defaultdict
import re
import logging

logger = logging.getLogger(__name__)


class SafetyAnalyzer:
    """안전도 분석 메인 클래스"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.calculator = CPTEDCalculator()
    
    def normalize_dong_name(self, dong_name):
        """동명 정규화 (매칭을 위해)"""
        if not dong_name:
            return ""
        
        # 숫자 제거 (예: 역삼1동 -> 역삼동)
        normalized = re.sub(r'\d+', '', dong_name)
        
        # 동/가동 통일
        normalized = normalized.replace('가동', '동')
        
        return normalized.strip()
    
    def collect_safety_data(self):
        """모든 안전 시설 데이터 수집"""
        
        logger.info("Collecting comprehensive safety data...")
        
        # 구/동별 안전 시설 통계를 저장할 딕셔너리
        dong_data = defaultdict(lambda: {
            'cctv_count': 0,
            'streetlight_count': 0,
            'police_station_count': 0,
            'female_safety_house_count': 0,
            'sexual_offender_count': 0,
            'delivery_box_count': 0
        })
        
        # 1. CCTV 데이터
        try:
            cctv_query = """
                SELECT district, dong, COUNT(*) as count
                FROM cctv_installations 
                WHERE district IS NOT NULL AND dong IS NOT NULL
                GROUP BY district, dong
            """
            cctv_results = self.db_manager.execute_query(cctv_query)
            
            for row in cctv_results:
                key = f"{row['district']}_{row['dong']}"
                dong_data[key]['district'] = row['district']
                dong_data[key]['dong'] = row['dong']
                dong_data[key]['cctv_count'] = row['count']
            
            logger.info(f"CCTV data collected: {len(cctv_results)} dong records")
        except Exception as e:
            logger.error(f"CCTV data collection error: {e}")
        
        # 2. 가로등 데이터
        try:
            streetlight_query = """
                SELECT district, dong, COUNT(*) as count
                FROM streetlight_installations 
                WHERE district IS NOT NULL AND dong IS NOT NULL
                GROUP BY district, dong
            """
            streetlight_results = self.db_manager.execute_query(streetlight_query)
            
            for row in streetlight_results:
                key = f"{row['district']}_{row['dong']}"
                if key not in dong_data:
                    dong_data[key]['district'] = row['district']
                    dong_data[key]['dong'] = row['dong']
                dong_data[key]['streetlight_count'] = row['count']
            
            logger.info(f"Streetlight data collected: {len(streetlight_results)} dong records")
        except Exception as e:
            logger.error(f"Streetlight data collection error: {e}")
        
        # 3. 경찰서 데이터
        try:
            police_query = """
                SELECT district_name as district, dong_name as dong, COUNT(*) as count
                FROM police_stations 
                WHERE district_name IS NOT NULL AND dong_name IS NOT NULL
                GROUP BY district_name, dong_name
            """
            police_results = self.db_manager.execute_query(police_query)
            
            # 동명 매칭을 통한 데이터 결합
            for row in police_results:
                police_district = row['district']
                police_dong = row['dong']
                
                # 가장 유사한 key 찾기
                best_match = None
                for key in dong_data.keys():
                    stored_district = dong_data[key].get('district', '')
                    stored_dong = dong_data[key].get('dong', '')
                    
                    if stored_district == police_district:
                        if self.normalize_dong_name(stored_dong) == self.normalize_dong_name(police_dong) or police_dong in stored_dong:
                            best_match = key
                            break
                
                if best_match:
                    dong_data[best_match]['police_station_count'] += row['count']
            
            logger.info(f"Police station data matched: {len(police_results)} dong records")
        except Exception as e:
            logger.error(f"Police station data collection error: {e}")
        
        # 4. 여성안심지킴이집 데이터
        try:
            safety_house_query = """
                SELECT district_name as district, dong_name as dong, COUNT(*) as count
                FROM female_safety_houses 
                WHERE district_name IS NOT NULL AND dong_name IS NOT NULL AND is_active = true
                GROUP BY district_name, dong_name
            """
            safety_house_results = self.db_manager.execute_query(safety_house_query)
            
            # 동명 매칭
            for row in safety_house_results:
                house_district = row['district']
                house_dong = row['dong']
                
                best_match = None
                for key in dong_data.keys():
                    stored_district = dong_data[key].get('district', '')
                    stored_dong = dong_data[key].get('dong', '')
                    
                    if stored_district == house_district:
                        if self.normalize_dong_name(stored_dong) == self.normalize_dong_name(house_dong) or house_dong in stored_dong:
                            best_match = key
                            break
                
                if best_match:
                    dong_data[best_match]['female_safety_house_count'] += row['count']
            
            logger.info(f"Female safety house data matched: {len(safety_house_results)} dong records")
        except Exception as e:
            logger.error(f"Female safety house data collection error: {e}")
        
        # 5. 성범죄자 데이터 (구별로 집계 후 분배)
        try:
            offender_query = """
                SELECT city_county_name, COUNT(*) as count
                FROM sexual_offender_addresses 
                WHERE city_county_name LIKE '%구'
                GROUP BY city_county_name
            """
            offender_results = self.db_manager.execute_query(offender_query)
            
            # 구별 성범죄자 수를 해당 구의 모든 동에 분배
            district_offenders = {}
            for row in offender_results:
                district_name = row['city_county_name']
                district_offenders[district_name] = row['count']
            
            # 각 구의 동 개수 계산
            district_dong_count = defaultdict(int)
            for key in dong_data.keys():
                district = dong_data[key].get('district', '')
                district_dong_count[district] += 1
            
            # 성범죄자 수를 동별로 분배
            for key in dong_data.keys():
                district = dong_data[key].get('district', '')
                if district in district_offenders and district in district_dong_count:
                    total_offenders = district_offenders[district]
                    dong_count = district_dong_count[district]
                    dong_data[key]['sexual_offender_count'] = total_offenders // dong_count
            
            logger.info(f"Sexual offender data distributed: {len(offender_results)} district records")
        except Exception as e:
            logger.error(f"Sexual offender data collection error: {e}")
        
        # 6. 안심택배함 데이터
        try:
            delivery_query = """
                SELECT district_name as district, dong_name as dong, COUNT(*) as count
                FROM safe_delivery_boxes 
                WHERE district_name IS NOT NULL AND dong_name IS NOT NULL
                GROUP BY district_name, dong_name
            """
            delivery_results = self.db_manager.execute_query(delivery_query)
            
            # 동명 매칭
            for row in delivery_results:
                delivery_district = row['district']
                delivery_dong = row['dong']
                
                best_match = None
                for key in dong_data.keys():
                    stored_district = dong_data[key].get('district', '')
                    stored_dong = dong_data[key].get('dong', '')
                    
                    if stored_district == delivery_district:
                        if self.normalize_dong_name(stored_dong) == self.normalize_dong_name(delivery_dong) or delivery_dong in stored_dong:
                            best_match = key
                            break
                
                if best_match:
                    dong_data[best_match]['delivery_box_count'] += row['count']
            
            logger.info(f"Safe delivery box data matched: {len(delivery_results)} dong records")
        except Exception as e:
            logger.error(f"Safe delivery box data collection error: {e}")
        
        return dong_data
    
    def calculate_safety_scores(self, dong_data):
        """안전도 점수 계산"""
        
        if not dong_data:
            logger.error("No safety data available for analysis")
            return []
        
        logger.info(f"Calculating safety scores for {len(dong_data)} dong areas...")
        
        safety_scores = []
        
        # 안전도 계산
        for i, (key, data) in enumerate(dong_data.items(), 1):
            district = data.get('district', '알 수 없음')
            dong = data.get('dong', '알 수 없음')
            
            # SafetyFactors 객체 생성
            factors = SafetyFactors(
                cctv_count=data['cctv_count'],
                streetlight_count=data['streetlight_count'],
                sexual_offender_count=data['sexual_offender_count'],
                police_station_count=data['police_station_count'],
                female_safety_house_count=data['female_safety_house_count'],
                delivery_box_count=data['delivery_box_count'],
                maintenance_score=0.6,  # 기본값
                activity_score=0.7      # 기본값
            )
            
            # 동 면적 (서울 평균: 2.4km²)
            area_size = 2.4
            
            # 안전도 계산
            score = self.calculator.calculate_safety_score(factors, area_size)
            
            safety_scores.append({
                'district': district,
                'dong': dong,
                'total_score': score.total_score,
                'grade': score.grade,
                'natural_surveillance': score.natural_surveillance,
                'access_control': score.access_control,
                'territoriality': score.territoriality,
                'maintenance': score.maintenance,
                'activity_support': score.activity_support,
                'cctv_count': data['cctv_count'],
                'streetlight_count': data['streetlight_count'],
                'police_station_count': data['police_station_count'],
                'female_safety_house_count': data['female_safety_house_count'],
                'sexual_offender_count': data['sexual_offender_count'],
                'delivery_box_count': data['delivery_box_count']
            })
            
            if i % 50 == 0:
                logger.info(f"Progress: {i}/{len(dong_data)} ({i/len(dong_data)*100:.1f}%)")
        
        return safety_scores
    
    def analyze_comprehensive_safety(self):
        """종합 안전도 분석 실행"""
        logger.info("Starting comprehensive safety analysis...")
        
        # 1. 데이터 수집
        dong_data = self.collect_safety_data()
        
        # 2. 안전도 계산
        safety_scores = self.calculate_safety_scores(dong_data)
        
        if not safety_scores:
            logger.error("No safety scores calculated")
            return None
        
        logger.info(f"Safety analysis completed for {len(safety_scores)} dong areas")
        return safety_scores
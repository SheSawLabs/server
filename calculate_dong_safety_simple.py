#!/usr/bin/env python3
"""
실제 데이터로 동별 안전도 간단 계산
"""

import sys
import os
sys.path.append('.')

from safety_score.cpted_calculator import CPTEDCalculator, SafetyFactors
from db.db_connection import get_db_manager

def calculate_dong_safety_simple():
    """CCTV 데이터 중심으로 동별 안전도 계산"""
    
    print("🔒 서울시 동별 안전도 계산 (CCTV 데이터 기반)")
    print("=" * 60)
    
    db = get_db_manager()
    calculator = CPTEDCalculator()
    
    # CCTV 데이터로 구/동별 안전 시설 현황 조회
    query = """
        SELECT 
            district,
            dong,
            COUNT(*) as cctv_count,
            SUM(cctv_count) as total_cctv  -- 실제 CCTV 대수
        FROM cctv_installations 
        WHERE district IS NOT NULL AND dong IS NOT NULL
        GROUP BY district, dong
        HAVING COUNT(*) >= 5  -- 최소 5개 이상 데이터가 있는 동만
        ORDER BY SUM(cctv_count) DESC
        LIMIT 30  -- 상위 30개 동
    """
    
    results = db.execute_query(query)
    
    if not results:
        print("❌ 데이터를 찾을 수 없습니다.")
        return
    
    print(f"📊 분석 대상: {len(results)}개 동 (CCTV 데이터 기준)")
    print()
    
    safety_scores = []
    
    for i, row in enumerate(results, 1):
        district = row['district']
        dong = row['dong'] 
        cctv_count = row['total_cctv'] or row['cctv_count']
        
        # 안전 요소 설정 (CCTV 중심)
        factors = SafetyFactors(
            cctv_count=cctv_count,
            streetlight_count=cctv_count // 2,  # CCTV 절반 정도로 추정
            sexual_offender_count=max(0, cctv_count // 50),  # CCTV 많은 곳일수록 성범죄자 적다고 가정
            police_station_count=1 if cctv_count > 100 else 0,
            female_safety_house_count=max(1, cctv_count // 30),
            delivery_box_count=max(1, cctv_count // 20),
            maintenance_score=0.7 if cctv_count > 200 else 0.5,
            activity_score=0.8 if cctv_count > 300 else 0.6
        )
        
        # 안전도 계산 (동 면적 2.4km²로 가정)
        area_size = 2.4
        safety_score = calculator.calculate_safety_score(factors, area_size)
        
        safety_scores.append({
            'district': district,
            'dong': dong,
            'cctv_count': cctv_count,
            'total_score': safety_score.total_score,
            'grade': safety_score.grade,
            'natural_surveillance': safety_score.natural_surveillance,
            'access_control': safety_score.access_control,
            'territoriality': safety_score.territoriality
        })
        
        print(f"{i:2d}. {district} {dong}")
        print(f"    CCTV: {cctv_count}대")
        print(f"    안전도: {safety_score.total_score:.1f}점 ({safety_score.grade}등급)")
        print(f"    자연적감시: {safety_score.natural_surveillance:.1f}점")
        print()
    
    # 결과 분석
    print("🎯 분석 결과:")
    
    # 등급별 분포
    grade_dist = {}
    for score in safety_scores:
        grade = score['grade']
        grade_dist[grade] = grade_dist.get(grade, 0) + 1
    
    print(f"\n📈 등급별 분포:")
    for grade in ['A', 'B', 'C', 'D', 'E']:
        count = grade_dist.get(grade, 0)
        percentage = (count / len(safety_scores) * 100) if safety_scores else 0
        print(f"   {grade}등급: {count}개 ({percentage:.1f}%)")
    
    # 상위 10개 동
    top_10 = sorted(safety_scores, key=lambda x: x['total_score'], reverse=True)[:10]
    print(f"\n🏆 안전도 상위 10개 동:")
    for i, score in enumerate(top_10, 1):
        print(f"   {i:2d}. {score['district']} {score['dong']}: {score['total_score']:.1f}점 ({score['grade']}등급)")
    
    # 하위 10개 동
    bottom_10 = sorted(safety_scores, key=lambda x: x['total_score'])[:10]
    print(f"\n⚠️  안전도 하위 10개 동:")
    for i, score in enumerate(bottom_10, 1):
        print(f"   {i:2d}. {score['district']} {score['dong']}: {score['total_score']:.1f}점 ({score['grade']}등급)")
    
    # CCTV와 안전도 상관관계
    high_cctv = [s for s in safety_scores if s['cctv_count'] > 300]
    if high_cctv:
        avg_score_high_cctv = sum(s['total_score'] for s in high_cctv) / len(high_cctv)
        print(f"\n📹 CCTV 300대 이상 지역 평균 안전도: {avg_score_high_cctv:.1f}점")
    
    low_cctv = [s for s in safety_scores if s['cctv_count'] <= 100]
    if low_cctv:
        avg_score_low_cctv = sum(s['total_score'] for s in low_cctv) / len(low_cctv)
        print(f"📹 CCTV 100대 이하 지역 평균 안전도: {avg_score_low_cctv:.1f}점")
    
    return safety_scores

if __name__ == "__main__":
    results = calculate_dong_safety_simple()
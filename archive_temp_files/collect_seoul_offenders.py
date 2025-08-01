#!/usr/bin/env python3
"""
서울시 성범죄자 데이터만 수집하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controllers.sexual_offender_controller import SexualOffenderController
from db.db_connection import get_db_manager

def main():
    print("🗑️ 기존 성범죄자 데이터 삭제 후 서울시만 새로 수집")
    print("=" * 60)
    
    # DB 연결
    db_manager = get_db_manager()
    
    # 1. 기존 데이터 모두 삭제
    print("🗑️ 기존 데이터 삭제 중...")
    delete_query = "DELETE FROM sexual_offender_addresses"
    db_manager.execute_non_query(delete_query)
    print("   ✅ 기존 데이터 삭제 완료")
    
    # 2. 서울시 데이터만 새로 수집
    print("\n🚀 서울시 성범죄자 데이터 수집 시작...")
    controller = SexualOffenderController()
    
    # 수집 실행 (서울시만)
    result = controller.run_full_collection_seoul_only()
    
    if result['success']:
        print(f"\n✅ 서울시 데이터 수집 완료!")
        print(f"   수집된 레코드: {result['records_saved']:,}개")
        print(f"   API 호출 수: {result['api_calls_used']:,}회")
        print(f"   처리된 페이지: {result['pages_processed']:,}개")
    else:
        print(f"\n❌ 수집 실패: {result.get('error')}")
    
    # 3. 최종 확인
    print(f"\n📊 최종 서울시 성범죄자 데이터 현황:")
    
    # 구별 통계
    district_query = """
    SELECT city_county_name, COUNT(*) as count
    FROM sexual_offender_addresses 
    WHERE city_province_name = '서울특별시'
    GROUP BY city_county_name
    ORDER BY count DESC
    """
    
    districts = db_manager.execute_query(district_query)
    total_seoul = sum([row['count'] for row in districts])
    
    print(f"   총 서울시 데이터: {total_seoul:,}개")
    print(f"   구별 분포 (상위 10개):")
    
    for i, row in enumerate(districts[:10], 1):
        district = row['city_county_name']
        count = row['count']
        percentage = (count / total_seoul * 100) if total_seoul > 0 else 0
        print(f"     {i:2d}. {district}: {count:,}개 ({percentage:.1f}%)")

if __name__ == "__main__":
    main()
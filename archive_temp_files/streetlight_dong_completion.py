#!/usr/bin/env python3
"""
가로등 동 정보 보완 시스템
"""

import sys
import os
import requests
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.db_connection import get_db_manager

class StreetlightDongCompletion:
    """가로등 동 정보 보완"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.kakao_api_key = os.getenv('KAKAO_API_KEY', '')
        
    def reverse_geocode_with_kakao(self, latitude, longitude):
        """카카오 API로 역지오코딩"""
        if not latitude or not longitude:
            return None, None
        
        url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
        headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
        params = {
            "x": str(longitude),
            "y": str(latitude),
            "input_coord": "WGS84"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    doc = data['documents'][0]
                    if 'address' in doc:
                        region_2depth = doc['address'].get('region_2depth_name')  # 구
                        region_3depth = doc['address'].get('region_3depth_name')  # 동
                        
                        # 구 정보 정리 (ex: "강남구" -> "강남구")
                        if region_2depth and not region_2depth.endswith('구'):
                            region_2depth = region_2depth + '구'
                        
                        # 동 정보 확인
                        if region_3depth and '동' in region_3depth:
                            return region_2depth, region_3depth
                        
            elif response.status_code == 429:
                time.sleep(1)  # API 제한시 대기
                return self.reverse_geocode_with_kakao(latitude, longitude)
                
        except Exception as e:
            pass
        
        return None, None
    
    def process_streetlights(self, batch_size=500):
        """가로등 동 정보 보완"""
        print("💡 가로등 동 정보 보완 시작...")
        
        # 동 정보가 없는 가로등 데이터 조회 (구별로 정렬)
        query = """
        SELECT id, district, dong, latitude, longitude, management_number
        FROM streetlight_installations 
        WHERE dong IS NULL OR dong = ''
        ORDER BY latitude, longitude
        """
        
        results = self.db_manager.execute_query(query)
        total = len(results)
        
        print(f"   처리 대상: {total:,}개")
        
        if total == 0:
            print("   ✅ 처리할 가로등 데이터가 없습니다.")
            return 0
        
        updated_count = 0
        api_call_count = 0
        
        for i, row in enumerate(results, 1):
            district_name = None
            dong_name = None
            
            # 좌표 기반 역지오코딩
            if row['latitude'] and row['longitude']:
                try:
                    district_name, dong_name = self.reverse_geocode_with_kakao(
                        float(row['latitude']), 
                        float(row['longitude'])
                    )
                    api_call_count += 1
                    time.sleep(0.05)  # API 제한 준수 (더 빠르게)
                except Exception as e:
                    pass
            
            # 구/동 정보 업데이트
            if district_name or dong_name:
                update_query = """
                UPDATE streetlight_installations 
                SET district = COALESCE(%s, district), 
                    dong = COALESCE(%s, dong),
                    updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s
                """
                self.db_manager.execute_non_query(
                    update_query, 
                    (district_name, dong_name, row['id'])
                )
                updated_count += 1
                
                print(f"   {i:5d}. {row['management_number']} → {district_name} {dong_name}")
            else:
                print(f"   {i:5d}. {row['management_number']} → 위치 정보 없음")
            
            # 진행률 출력
            if i % batch_size == 0 or i == total:
                completion_rate = (updated_count / i) * 100 if i > 0 else 0
                print(f"       진행: {i:,}/{total:,} ({i/total*100:.1f}%) - 업데이트: {updated_count:,}개 ({completion_rate:.1f}%)")
                print(f"       API 호출: {api_call_count:,}회")
        
        print(f"   ✅ 가로등 처리 완료: {updated_count:,}/{total:,}개")
        return updated_count
    
    def final_completion_report(self):
        """최종 완성도 보고서"""
        print(f"\n📋 가로등 동 정보 완성도 보고서")
        print("=" * 60)
        
        # 가로등 최종 통계
        streetlight_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM streetlight_installations
        """
        
        streetlight_result = self.db_manager.execute_query(streetlight_query)[0]
        
        print(f"💡 가로등 최종 현황:")
        print(f"   총 데이터: {streetlight_result['total']:,}개")
        print(f"   완성된 데이터: {streetlight_result['completed']:,}개")
        print(f"   완성도: {streetlight_result['rate']}%")
        
        # 구별 완성도 (상위 10개)
        district_query = """
        SELECT 
            district,
            COUNT(*) as total,
            COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM streetlight_installations
        WHERE district IS NOT NULL AND district <> ''
        GROUP BY district
        ORDER BY rate DESC, completed DESC
        LIMIT 10
        """
        
        district_results = self.db_manager.execute_query(district_query)
        
        print(f"\n🏆 구별 완성도 순위 (상위 10개):")
        for i, row in enumerate(district_results, 1):
            district = row['district'] or '미분류'
            completed = row['completed']
            total = row['total']
            rate = row['rate']
            
            print(f"   {i:2d}. {district:10s}: {completed:,}/{total:,} ({rate:5.1f}%)")

def main():
    """가로등 동 정보 보완 실행"""
    print("🚀 가로등 동 정보 보완 시스템")
    print("=" * 60)
    
    processor = StreetlightDongCompletion()
    
    start_time = time.time()
    
    # 가로등 처리
    streetlight_updated = processor.process_streetlights(batch_size=500)
    
    # 최종 보고서
    processor.final_completion_report()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n⚡ 처리 완료!")
    print(f"   가로등: {streetlight_updated:,}개")
    print(f"   소요 시간: {total_time:.1f}초")

if __name__ == "__main__":
    main()
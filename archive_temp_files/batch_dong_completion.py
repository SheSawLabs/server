#!/usr/bin/env python3
"""
완성도 낮은 구 집중 처리 시스템
"""

import sys
import os
import requests
import time
import re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.db_connection import get_db_manager

class BatchDongCompletion:
    """완성도 낮은 구 집중 처리"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.kakao_api_key = os.getenv('KAKAO_API_KEY', '')
        
        # 완성도 0%인 구들
        self.target_districts = ['강남구', '광진구', '성북구', '강북구', '도봉구']
    
    def analyze_low_completion_districts(self):
        """완성도 낮은 구들 상세 분석"""
        print("🎯 완성도 낮은 구들 집중 분석...")
        
        for district in self.target_districts:
            print(f"\n📍 {district} 분석:")
            
            # 기본 통계
            stats_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN dong IS NOT NULL AND dong != '' THEN 1 END) as has_dong,
                COUNT(CASE WHEN address IS NOT NULL AND address != '' THEN 1 END) as has_address,
                COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as has_coords
            FROM cctv_installations 
            WHERE district = %s
            """
            
            result = self.db_manager.execute_query(stats_query, (district,))[0]
            
            print(f"   전체: {result['total']:,}개")
            print(f"   동 정보: {result['has_dong']:,}개")
            print(f"   주소 정보: {result['has_address']:,}개")
            print(f"   좌표 정보: {result['has_coords']:,}개")
            
            # 주소 샘플 확인
            sample_query = """
            SELECT address FROM cctv_installations 
            WHERE district = %s AND address IS NOT NULL 
            LIMIT 3
            """
            
            samples = self.db_manager.execute_query(sample_query, (district,))
            print(f"   주소 샘플:")
            for sample in samples:
                print(f"     - {sample['address']}")
    
    def extract_dong_from_address_enhanced(self, address):
        """향상된 주소 파싱"""
        if not address:
            return None
        
        # 더 다양한 동명 패턴
        dong_patterns = [
            r'([가-힣]+\d*동)(?:\s|$|[^\w])',      # 기본 동명
            r'([가-힣]+\d*가동)(?:\s|$|[^\w])',    # 가동
            r'([가-힣]+\d*로동)(?:\s|$|[^\w])',    # 로동
            r'([가-힣]+\d*리동)(?:\s|$|[^\w])',    # 리동
            r'([가-힣]+\d*본동)(?:\s|$|[^\w])',    # 본동
            r'([가-힣]+\d*신동)(?:\s|$|[^\w])',    # 신동
            r'(?:서울\s*)?[가-힣]+구\s*([가-힣]+\d*동)', # 구명 다음 동명
        ]
        
        for pattern in dong_patterns:
            match = re.search(pattern, address)
            if match:
                dong_name = match.group(1)
                # 필터링: 너무 짧거나 이상한 패턴 제외
                if len(dong_name) >= 2 and not dong_name.endswith('건동'):
                    return dong_name
        
        return None
    
    def batch_process_district(self, district, limit=1000):
        """특정 구 일괄 처리"""
        print(f"\n🚀 {district} 일괄 처리 시작 (최대 {limit}개)...")
        
        # 동 정보가 없는 데이터 조회
        missing_query = """
        SELECT id, address, latitude, longitude
        FROM cctv_installations 
        WHERE district = %s 
        AND (dong IS NULL OR dong = '')
        AND (address IS NOT NULL OR (latitude IS NOT NULL AND longitude IS NOT NULL))
        LIMIT %s
        """
        
        results = self.db_manager.execute_query(missing_query, (district, limit))
        
        if not results:
            print(f"   ✅ {district}에 처리할 데이터가 없습니다.")
            return 0
        
        print(f"   처리 대상: {len(results)}개")
        
        address_updated = 0
        geocoding_updated = 0
        
        # 1단계: 주소 파싱
        print(f"   📝 1단계: 주소 파싱...")
        for i, row in enumerate(results, 1):
            if row['address']:
                dong_name = self.extract_dong_from_address_enhanced(row['address'])
                if dong_name:
                    # 동 정보 업데이트
                    update_query = """
                    UPDATE cctv_installations 
                    SET dong = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = %s
                    """
                    self.db_manager.execute_non_query(update_query, (dong_name, row['id']))
                    address_updated += 1
            
            if i % 200 == 0:
                print(f"      진행: {i}/{len(results)} - 주소파싱: {address_updated}개")
        
        print(f"   ✅ 주소 파싱 완료: {address_updated}개")
        
        # 2단계: 지오코딩 (주소 파싱 실패한 것들)
        remaining_query = """
        SELECT id, latitude, longitude
        FROM cctv_installations 
        WHERE district = %s 
        AND (dong IS NULL OR dong = '')
        AND latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT 500
        """
        
        remaining = self.db_manager.execute_query(remaining_query, (district, ))
        
        if remaining:
            print(f"   🗺️ 2단계: 지오코딩 ({len(remaining)}개)...")
            
            for i, row in enumerate(remaining, 1):
                try:
                    dong_name = self.reverse_geocode_with_kakao(
                        float(row['latitude']), 
                        float(row['longitude'])
                    )
                    
                    if dong_name:
                        update_query = """
                        UPDATE cctv_installations 
                        SET dong = %s, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                        """
                        self.db_manager.execute_non_query(update_query, (dong_name, row['id']))
                        geocoding_updated += 1
                    
                    # API 제한 준수
                    time.sleep(0.1)
                    
                    if i % 50 == 0:
                        print(f"      진행: {i}/{len(remaining)} - 지오코딩: {geocoding_updated}개")
                        time.sleep(1)  # 추가 쿨타임
                
                except Exception as e:
                    print(f"      오류 (ID: {row['id']}): {e}")
                    continue
        
        total_updated = address_updated + geocoding_updated
        print(f"   🎯 {district} 완료: 총 {total_updated}개 (주소: {address_updated}, 지오코딩: {geocoding_updated})")
        
        return total_updated
    
    def reverse_geocode_with_kakao(self, latitude, longitude):
        """카카오 API로 역지오코딩 (에러 처리 강화)"""
        url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
        headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
        params = {
            "x": str(longitude),
            "y": str(latitude),
            "input_coord": "WGS84"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    doc = data['documents'][0]
                    if 'address' in doc:
                        region_3depth = doc['address'].get('region_3depth_name')
                        if region_3depth and '동' in region_3depth:
                            return region_3depth
            elif response.status_code == 429:
                # API 제한 초과
                print(f"      API 제한 - 5초 대기...")
                time.sleep(5)
                return self.reverse_geocode_with_kakao(latitude, longitude)
                
        except Exception as e:
            print(f"      지오코딩 API 오류: {e}")
        
        return None
    
    def verify_completion_improvement(self):
        """완성도 개선 효과 확인"""
        print(f"\n📊 완성도 개선 효과 확인:")
        print("-" * 50)
        
        for district in self.target_districts:
            stats_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN dong IS NOT NULL AND dong != '' THEN 1 END) as completed,
                ROUND(
                    COUNT(CASE WHEN dong IS NOT NULL AND dong != '' THEN 1 END) * 100.0 / COUNT(*), 1
                ) as completion_rate
            FROM cctv_installations 
            WHERE district = %s
            """
            
            result = self.db_manager.execute_query(stats_query, (district,))[0]
            
            total = result['total']
            completed = result['completed']
            rate = result['completion_rate']
            
            print(f"{district:8s}: {completed:4d}/{total:4d} ({rate:5.1f}%)")
    
    def get_district_dong_summary(self, district):
        """구별 동 현황 요약"""
        dong_summary_query = """
        SELECT dong, COUNT(*) as count
        FROM cctv_installations 
        WHERE district = %s AND dong IS NOT NULL AND dong != ''
        GROUP BY dong
        ORDER BY count DESC
        LIMIT 10
        """
        
        results = self.db_manager.execute_query(dong_summary_query, (district,))
        
        if results:
            print(f"\n🏆 {district} 상위 동별 CCTV 현황:")
            for i, row in enumerate(results, 1):
                print(f"   {i:2d}. {row['dong']}: {row['count']:,}개")
        else:
            print(f"   {district}에 동 정보가 있는 데이터가 없습니다.")

def main():
    """완성도 낮은 구 집중 처리 실행"""
    print("🎯 완성도 낮은 구 집중 처리 시스템")
    print("=" * 60)
    
    processor = BatchDongCompletion()
    
    # 1. 현황 분석
    processor.analyze_low_completion_districts()
    
    print(f"\n" + "="*60)
    print("🚀 일괄 처리 시작")
    
    total_processed = 0
    
    # 2. 각 구별 일괄 처리
    for district in processor.target_districts:
        processed = processor.batch_process_district(district, limit=2000)
        total_processed += processed
        
        # 구별 결과 요약
        processor.get_district_dong_summary(district)
        
        print(f"\n{'='*30}")
    
    # 3. 최종 결과 확인
    print(f"\n🎉 전체 처리 완료!")
    print(f"총 처리된 데이터: {total_processed:,}개")
    
    processor.verify_completion_improvement()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
지오코딩 및 주소 파싱 기반 동 정보 보완 시스템
"""

import sys
import os
import re
import requests
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.db_connection import get_db_manager

class DongInfoEnhancement:
    """동 정보 보완 시스템"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        # 카카오 API 키
        self.kakao_api_key = os.getenv('KAKAO_API_KEY', '')
    
    def analyze_missing_dong_data(self):
        """동 정보 누락 현황 분석"""
        print("🔍 동 정보 누락 현황 분석...")
        
        analysis_query = """
        SELECT 
            district,
            COUNT(*) as total_count,
            COUNT(CASE WHEN dong IS NOT NULL AND dong != '' THEN 1 END) as has_dong,
            COUNT(CASE WHEN dong IS NULL OR dong = '' THEN 1 END) as missing_dong,
            ROUND(
                COUNT(CASE WHEN dong IS NOT NULL AND dong != '' THEN 1 END) * 100.0 / COUNT(*), 1
            ) as dong_completion_rate
        FROM cctv_installations 
        GROUP BY district 
        ORDER BY missing_dong DESC
        """
        
        results = self.db_manager.execute_query(analysis_query)
        
        print(f"\n📊 구별 동 정보 완성도:")
        print("-" * 60)
        total_missing = 0
        for row in results:
            district = row['district']
            total = row['total_count']
            has_dong = row['has_dong']
            missing = row['missing_dong']
            rate = row['dong_completion_rate']
            
            total_missing += missing
            print(f"{district:8s}: {has_dong:5d}/{total:5d} ({rate:5.1f}%) - 누락: {missing:5d}개")
        
        print(f"\n🎯 전체 누락 동 정보: {total_missing:,}개")
        return results
    
    def extract_dong_from_address(self, address):
        """주소에서 동 정보 추출"""
        if not address:
            return None
        
        # 동명 패턴 매칭 (숫자+동, 한글+동)
        dong_patterns = [
            r'([가-힣]+\d*동)',        # 신림동, 역삼1동 등
            r'([가-힣]+\d*가동)',      # 종로1가동 등
            r'([가-힣]+\d*로동)',      # 을지로동 등
        ]
        
        for pattern in dong_patterns:
            match = re.search(pattern, address)
            if match:
                return match.group(1)
        
        return None
    
    def update_dong_from_address_parsing(self):
        """주소 파싱으로 동 정보 업데이트"""
        print("\n📝 주소 파싱 기반 동 정보 보완...")
        
        # 동 정보가 없지만 주소가 있는 데이터 조회
        missing_dong_query = """
        SELECT id, district, address, latitude, longitude
        FROM cctv_installations 
        WHERE (dong IS NULL OR dong = '') 
        AND address IS NOT NULL AND address != ''
        LIMIT 1000
        """
        
        results = self.db_manager.execute_query(missing_dong_query)
        print(f"   처리 대상: {len(results)}개")
        
        updated_count = 0
        for i, row in enumerate(results, 1):
            address = row['address']
            extracted_dong = self.extract_dong_from_address(address)
            
            if extracted_dong:
                # 동 정보 업데이트
                update_query = """
                UPDATE cctv_installations 
                SET dong = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s
                """
                self.db_manager.execute_non_query(update_query, (extracted_dong, row['id']))
                updated_count += 1
                
                if i % 100 == 0:
                    print(f"   진행률: {i:4d}/{len(results)} ({i/len(results)*100:.1f}%) - 업데이트: {updated_count}개")
        
        print(f"   ✅ 주소 파싱 완료: {updated_count}개 동 정보 추가")
        return updated_count
    
    def reverse_geocode_with_kakao(self, latitude, longitude):
        """카카오 API로 역지오코딩"""
        if not latitude or not longitude:
            return None
        
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
                
                # 법정동 정보 추출
                if data['documents']:
                    doc = data['documents'][0]
                    if 'address' in doc:
                        address_info = doc['address']
                        return {
                            'region_1depth_name': address_info.get('region_1depth_name'),  # 시/도
                            'region_2depth_name': address_info.get('region_2depth_name'),  # 구
                            'region_3depth_name': address_info.get('region_3depth_name'),  # 동
                        }
            return None
        except Exception as e:
            print(f"   API 오류: {e}")
            return None
    
    def update_dong_from_geocoding(self, limit=100):
        """지오코딩으로 동 정보 업데이트"""
        print(f"\n🗺️ 지오코딩 기반 동 정보 보완 (최대 {limit}개)...")
        
        # 주소 파싱으로도 찾지 못한 데이터 조회
        remaining_query = """
        SELECT id, district, address, latitude, longitude
        FROM cctv_installations 
        WHERE (dong IS NULL OR dong = '') 
        AND latitude IS NOT NULL AND longitude IS NOT NULL
        AND latitude != 0 AND longitude != 0
        LIMIT %s
        """
        
        results = self.db_manager.execute_query(remaining_query, (limit,))
        print(f"   처리 대상: {len(results)}개")
        
        if len(results) == 0:
            print("   ✅ 지오코딩이 필요한 데이터가 없습니다.")
            return 0
        
        updated_count = 0
        for i, row in enumerate(results, 1):
            lat = float(row['latitude'])
            lng = float(row['longitude'])
            
            # 카카오 API 호출
            geo_result = self.reverse_geocode_with_kakao(lat, lng)
            
            if geo_result and geo_result['region_3depth_name']:
                dong_name = geo_result['region_3depth_name']
                
                # 동 정보 업데이트
                update_query = """
                UPDATE cctv_installations 
                SET dong = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s
                """
                self.db_manager.execute_non_query(update_query, (dong_name, row['id']))
                updated_count += 1
                
                print(f"   {i:3d}. {row['district']} → {dong_name} (위도: {lat:.4f}, 경도: {lng:.4f})")
            
            # API 호출 제한 준수 (초당 10회)
            time.sleep(0.1)
            
            if i % 10 == 0:
                print(f"   진행률: {i:3d}/{len(results)} ({i/len(results)*100:.1f}%) - 업데이트: {updated_count}개")
        
        print(f"   ✅ 지오코딩 완료: {updated_count}개 동 정보 추가")
        return updated_count
    
    def verify_dong_consistency(self):
        """동 정보 일관성 검증"""
        print(f"\n🔍 동 정보 일관성 검증...")
        
        # 구와 동의 조합이 올바른지 검증
        consistency_query = """
        SELECT district, dong, COUNT(*) as count
        FROM cctv_installations 
        WHERE dong IS NOT NULL AND dong != ''
        GROUP BY district, dong
        ORDER BY district, dong
        """
        
        results = self.db_manager.execute_query(consistency_query)
        
        print(f"   총 {len(results)}개의 구-동 조합 발견")
        
        # 의심스러운 조합 찾기 (예: 강남구에 신림동이 있는 경우)
        suspicious_combinations = []
        for row in results:
            district = row['district']
            dong = row['dong']
            count = row['count']
            
            # 간단한 검증 로직 (실제로는 더 정교한 검증 필요)
            if count < 5:  # 너무 적은 데이터는 의심스러움
                suspicious_combinations.append((district, dong, count))
        
        if suspicious_combinations:
            print(f"   ⚠️ 의심스러운 조합 {len(suspicious_combinations)}개:")
            for district, dong, count in suspicious_combinations[:10]:
                print(f"     {district} {dong}: {count}개")
        else:
            print(f"   ✅ 모든 구-동 조합이 정상적입니다.")
    
    def create_dong_completion_report(self):
        """동 정보 보완 완료 보고서"""
        print(f"\n📋 동 정보 보완 완료 보고서")
        print("=" * 50)
        
        # 최종 완성도 확인
        final_stats_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN dong IS NOT NULL AND dong != '' THEN 1 END) as completed,
            COUNT(CASE WHEN dong IS NULL OR dong = '' THEN 1 END) as remaining,
            ROUND(
                COUNT(CASE WHEN dong IS NOT NULL AND dong != '' THEN 1 END) * 100.0 / COUNT(*), 1
            ) as completion_rate
        FROM cctv_installations
        """
        
        result = self.db_manager.execute_query(final_stats_query)[0]
        
        print(f"전체 CCTV 데이터: {result['total']:,}개")
        print(f"동 정보 완료: {result['completed']:,}개")
        print(f"동 정보 누락: {result['remaining']:,}개")
        print(f"완성도: {result['completion_rate']}%")
        
        # 구별 상위 동 현황
        top_dong_query = """
        SELECT district, dong, COUNT(*) as count
        FROM cctv_installations 
        WHERE dong IS NOT NULL AND dong != ''
        GROUP BY district, dong
        ORDER BY count DESC
        LIMIT 10
        """
        
        top_results = self.db_manager.execute_query(top_dong_query)
        
        print(f"\n🏆 CCTV 최다 설치 상위 10개 동:")
        for i, row in enumerate(top_results, 1):
            print(f"   {i:2d}. {row['district']} {row['dong']}: {row['count']:,}개")

def main():
    """동 정보 보완 시스템 실행"""
    print("🗺️ 동 정보 보완 시스템 시작")
    print("=" * 50)
    
    enhancer = DongInfoEnhancement()
    
    # 1. 현황 분석
    enhancer.analyze_missing_dong_data()
    
    # 2. 주소 파싱으로 동 정보 보완
    address_updated = enhancer.update_dong_from_address_parsing()
    
    # 3. 지오코딩으로 추가 보완 (제한적으로)
    if address_updated > 0:
        print(f"\n🔄 주소 파싱으로 {address_updated}개 보완 완료!")
        
    # 소량의 데이터로 지오코딩 테스트
    geo_updated = enhancer.update_dong_from_geocoding(limit=50)
    
    # 4. 일관성 검증
    enhancer.verify_dong_consistency()
    
    # 5. 완료 보고서
    enhancer.create_dong_completion_report()
    
    print(f"\n✨ 동 정보 보완 시스템 완료!")
    print(f"   주소 파싱: {address_updated}개")
    print(f"   지오코딩: {geo_updated}개")
    print(f"   총 보완: {address_updated + geo_updated}개")

if __name__ == "__main__":
    main()
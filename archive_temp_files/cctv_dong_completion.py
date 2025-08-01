#!/usr/bin/env python3
"""
CCTV 동 정보 보완 시스템
"""

import sys
import os
import requests
import time
import re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.db_connection import get_db_manager

class CCTVDongCompletion:
    """CCTV 동 정보 보완"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.kakao_api_key = os.getenv('KAKAO_API_KEY', '')
        
    def extract_dong_from_address(self, address):
        """주소에서 동명 추출 시도"""
        if not address:
            return None
        
        # 동명 추출 패턴들
        patterns = [
            r'([가-힣]+\d*동)(?:[^\w가-힣]|$)',
            r'([가-힣]+\d*로동)(?:[^\w가-힣]|$)',
            r'([가-힣]+\d*본동)(?:[^\w가-힣]|$)',
            r'([가-힣]+\d*신동)(?:[^\w가-힣]|$)',
            r'\(([가-힣]+\d*동)\)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, address)
            for match in matches:
                dong_name = match.strip()
                if (len(dong_name) >= 2 and 
                    dong_name.endswith('동') and 
                    not dong_name.startswith('건') and
                    not dong_name.startswith('층')):
                    return dong_name
        
        return None
        
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
    
    def process_cctv(self, batch_size=1000):
        """CCTV 동 정보 보완"""
        print("📹 CCTV 동 정보 보완 시작...")
        
        # 동 정보가 없는 CCTV 데이터 조회 (구별로 정렬)
        query = """
        SELECT id, district, dong, address, latitude, longitude, cctv_count
        FROM cctv_installations 
        WHERE dong IS NULL OR dong = ''
        ORDER BY district, latitude, longitude
        """
        
        results = self.db_manager.execute_query(query)
        total = len(results)
        
        print(f"   처리 대상: {total:,}개")
        
        if total == 0:
            print("   ✅ 처리할 CCTV 데이터가 없습니다.")
            return 0
        
        updated_count = 0
        api_call_count = 0
        
        for i, row in enumerate(results, 1):
            district_name = row['district']  # 기존 구 정보 유지
            dong_name = None
            
            # 1단계: 주소에서 동명 추출
            if row['address']:
                dong_name = self.extract_dong_from_address(row['address'])
            
            # 2단계: 좌표 기반 역지오코딩 (주소 추출 실패시)
            if not dong_name and row['latitude'] and row['longitude']:
                try:
                    api_district, api_dong = self.reverse_geocode_with_kakao(
                        float(row['latitude']), 
                        float(row['longitude'])
                    )
                    
                    # API에서 받은 동 정보 사용
                    if api_dong:
                        dong_name = api_dong
                    
                    # 구 정보가 비어있으면 API 결과 사용
                    if not district_name and api_district:
                        district_name = api_district
                    
                    api_call_count += 1
                    time.sleep(0.05)  # API 제한 준수
                except Exception as e:
                    pass
            
            # 동 정보 업데이트
            if dong_name:
                update_query = """
                UPDATE cctv_installations 
                SET district = COALESCE(%s, district), 
                    dong = %s,
                    updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s
                """
                self.db_manager.execute_non_query(
                    update_query, 
                    (district_name, dong_name, row['id'])
                )
                updated_count += 1
                
                address_preview = (row['address'][:30] + '...') if row['address'] and len(row['address']) > 30 else row['address']
                print(f"   {i:5d}. {address_preview} → {district_name} {dong_name}")
            else:
                address_preview = (row['address'][:30] + '...') if row['address'] and len(row['address']) > 30 else row['address']
                print(f"   {i:5d}. {address_preview} → 동 정보 없음")
            
            # 진행률 출력
            if i % batch_size == 0 or i == total:
                completion_rate = (updated_count / i) * 100 if i > 0 else 0
                print(f"       진행: {i:,}/{total:,} ({i/total*100:.1f}%) - 업데이트: {updated_count:,}개 ({completion_rate:.1f}%)")
                print(f"       API 호출: {api_call_count:,}회")
        
        print(f"   ✅ CCTV 처리 완료: {updated_count:,}/{total:,}개")
        return updated_count
    
    def final_completion_report(self):
        """최종 완성도 보고서"""
        print(f"\n📋 CCTV 동 정보 완성도 보고서")
        print("=" * 60)
        
        # CCTV 최종 통계
        cctv_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM cctv_installations
        """
        
        cctv_result = self.db_manager.execute_query(cctv_query)[0]
        
        print(f"📹 CCTV 최종 현황:")
        print(f"   총 데이터: {cctv_result['total']:,}개")
        print(f"   완성된 데이터: {cctv_result['completed']:,}개")
        print(f"   완성도: {cctv_result['rate']}%")
        
        # 구별 완성도 (상위 15개)
        district_query = """
        SELECT 
            district,
            COUNT(*) as total,
            COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM cctv_installations
        WHERE district IS NOT NULL AND district <> ''
        GROUP BY district
        ORDER BY rate DESC, completed DESC
        LIMIT 15
        """
        
        district_results = self.db_manager.execute_query(district_query)
        
        print(f"\n🏆 구별 완성도 순위 (상위 15개):")
        for i, row in enumerate(district_results, 1):
            district = row['district'] or '미분류'
            completed = row['completed']
            total = row['total']
            rate = row['rate']
            
            print(f"   {i:2d}. {district:10s}: {completed:,}/{total:,} ({rate:5.1f}%)")

def main():
    """CCTV 동 정보 보완 실행"""
    print("🚀 CCTV 동 정보 보완 시스템")
    print("=" * 60)
    
    processor = CCTVDongCompletion()
    
    start_time = time.time()
    
    # CCTV 처리
    cctv_updated = processor.process_cctv(batch_size=1000)
    
    # 최종 보고서
    processor.final_completion_report()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n⚡ 처리 완료!")
    print(f"   CCTV: {cctv_updated:,}개")
    print(f"   소요 시간: {total_time:.1f}초")

if __name__ == "__main__":
    main()
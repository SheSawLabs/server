#!/usr/bin/env python3
"""
초고속 동 정보 보완 시스템 - 모든 데이터 처리
"""

import sys
import os
import re
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.db_connection import get_db_manager

class FastDongCompletion:
    """초고속 동 정보 보완"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.kakao_api_key = os.getenv('KAKAO_API_KEY', '')
        self.processed_count = 0
        
    def enhanced_address_parsing(self, address):
        """향상된 주소 파싱 - 더 많은 패턴 매칭"""
        if not address:
            return None
        
        # 더 공격적인 동명 추출 패턴
        patterns = [
            # 기본 패턴들
            r'([가-힣]+\d*동)(?:[^\w가-힣]|$)',
            r'([가-힣]+\d*가동)(?:[^\w가-힣]|$)',
            r'([가-힣]+\d*로동)(?:[^\w가-힣]|$)',
            r'([가-힣]+\d*본동)(?:[^\w가-힣]|$)',
            
            # 괄호 안의 동명
            r'\(([가-힣]+\d*동)\)',
            r'\[([가-힣]+\d*동)\]',
            
            # 구분자 다음 동명
            r'[_\-\s]([가-힣]+\d*동)',
            r'([가-힣]+\d*동)[_\-\s]',
            
            # 숫자 코드 다음 동명
            r'[A-Z]\d+[^\w]*([가-힣]+\d*동)',
            
            # 주소 형태에서 동명 추출
            r'(?:서울\s*)?[가-힣]+구\s*([가-힣]+\d*동)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, address)
            for match in matches:
                dong_name = match.strip()
                # 유효한 동명인지 검증 (길이, 패턴)
                if (len(dong_name) >= 2 and 
                    dong_name.endswith('동') and 
                    not dong_name.startswith('건') and
                    not dong_name.startswith('층')):
                    return dong_name
        
        return None
    
    def batch_address_parsing(self, batch_size=5000):
        """대량 주소 파싱 처리"""
        print("🚀 1단계: 대량 주소 파싱 시작...")
        
        # 동 정보가 없고 주소가 있는 모든 데이터 조회
        query = """
        SELECT id, district, address 
        FROM cctv_installations 
        WHERE (dong IS NULL OR dong = '') 
        AND address IS NOT NULL AND address <> ''
        ORDER BY district
        """
        
        results = self.db_manager.execute_query(query)
        total = len(results)
        
        print(f"   대상 데이터: {total:,}개")
        
        if total == 0:
            print("   ✅ 처리할 데이터가 없습니다.")
            return 0
        
        updated_count = 0
        update_batch = []
        
        # 배치 단위로 처리
        for i, row in enumerate(results, 1):
            dong_name = self.enhanced_address_parsing(row['address'])
            
            if dong_name:
                update_batch.append((dong_name, row['id']))
                updated_count += 1
            
            # 배치 크기마다 DB 업데이트
            if len(update_batch) >= batch_size or i == total:
                if update_batch:
                    self.batch_update_dong(update_batch)
                    update_batch = []
                
                # 진행률 출력
                if i % 10000 == 0 or i == total:
                    print(f"   진행: {i:,}/{total:,} ({i/total*100:.1f}%) - 파싱: {updated_count:,}개")
        
        print(f"   ✅ 주소 파싱 완료: {updated_count:,}개")
        return updated_count
    
    def batch_update_dong(self, update_batch):
        """배치 단위 DB 업데이트"""
        if not update_batch:
            return
        
        # 간단한 개별 업데이트로 변경
        query = """
        UPDATE cctv_installations 
        SET dong = %s, updated_at = CURRENT_TIMESTAMP 
        WHERE id = %s
        """
        
        try:
            for dong_name, cctv_id in update_batch:
                self.db_manager.execute_non_query(query, (dong_name, cctv_id))
        except Exception as e:
            print(f"   배치 업데이트 오류: {e}")
    
    def smart_geocoding_batch(self, limit=2000):
        """스마트 지오코딩 - 구별로 균등하게 처리"""
        print(f"\n🗺️ 2단계: 스마트 지오코딩 ({limit}개 제한)...")
        
        # 구별로 남은 데이터 수 확인
        district_query = """
        SELECT district, COUNT(*) as remaining_count
        FROM cctv_installations 
        WHERE (dong IS NULL OR dong = '') 
        AND latitude IS NOT NULL AND longitude IS NOT NULL
        GROUP BY district
        ORDER BY remaining_count DESC
        """
        
        district_stats = self.db_manager.execute_query(district_query)
        
        if not district_stats:
            print("   ✅ 지오코딩할 데이터가 없습니다.")
            return 0
        
        print("   구별 남은 데이터:")
        for row in district_stats:
            print(f"     {row['district']}: {row['remaining_count']:,}개")
        
        # 각 구별로 균등하게 할당
        per_district_limit = max(1, limit // len(district_stats))
        total_geocoded = 0
        
        for district_info in district_stats:
            district = district_info['district']
            geocoded = self.geocode_district_batch(district, per_district_limit)
            total_geocoded += geocoded
            
            if total_geocoded >= limit:
                break
        
        print(f"   ✅ 지오코딩 완료: {total_geocoded:,}개")
        return total_geocoded
    
    def geocode_district_batch(self, district, limit):
        """구별 지오코딩 처리"""
        query = """
        SELECT id, latitude, longitude
        FROM cctv_installations 
        WHERE district = %s 
        AND (dong IS NULL OR dong = '') 
        AND latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT %s
        """
        
        results = self.db_manager.execute_query(query, (district, limit))
        
        if not results:
            return 0
        
        print(f"     {district}: {len(results)}개 지오코딩 중...")
        
        geocoded_count = 0
        
        for i, row in enumerate(results, 1):
            try:
                dong_name = self.fast_reverse_geocode(
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
                    geocoded_count += 1
                
                # API 제한 최소화 (더 빠르게)
                time.sleep(0.05)  # 50ms 대기
                
            except Exception as e:
                if "429" in str(e):  # API 제한
                    print(f"       API 제한 - 잠시 대기...")
                    time.sleep(2)
                continue
        
        return geocoded_count
    
    def fast_reverse_geocode(self, lat, lng):
        """빠른 역지오코딩"""
        url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
        headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
        params = {"x": str(lng), "y": str(lat), "input_coord": "WGS84"}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                if data['documents'] and data['documents'][0].get('address'):
                    region_3depth = data['documents'][0]['address'].get('region_3depth_name')
                    if region_3depth and '동' in region_3depth:
                        return region_3depth
            
        except:
            pass
        
        return None
    
    def final_completion_report(self):
        """최종 완성도 보고서"""
        print(f"\n📋 최종 동 정보 완성도 보고서")
        print("=" * 60)
        
        # 전체 통계
        total_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM cctv_installations
        """
        
        total_result = self.db_manager.execute_query(total_query)[0]
        
        print(f"🎯 전체 현황:")
        print(f"   총 데이터: {total_result['total']:,}개")
        print(f"   완성된 데이터: {total_result['completed']:,}개")
        print(f"   전체 완성도: {total_result['rate']}%")
        
        # 구별 완성도 (상위 10개)
        district_query = """
        SELECT 
            district,
            COUNT(*) as total,
            COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM cctv_installations 
        GROUP BY district
        ORDER BY rate DESC, completed DESC
        LIMIT 15
        """
        
        district_results = self.db_manager.execute_query(district_query)
        
        print(f"\n🏆 구별 완성도 순위:")
        for i, row in enumerate(district_results, 1):
            district = row['district']
            completed = row['completed']
            total = row['total']
            rate = row['rate']
            
            print(f"   {i:2d}. {district:8s}: {completed:4d}/{total:4d} ({rate:5.1f}%)")
        
        # 남은 작업량
        remaining_query = """
        SELECT COUNT(*) as remaining
        FROM cctv_installations 
        WHERE dong IS NULL OR dong = ''
        """
        
        remaining = self.db_manager.execute_query(remaining_query)[0]['remaining']
        print(f"\n⚠️ 남은 작업: {remaining:,}개")
        
        if remaining > 0:
            print(f"   → 추가 처리하면 최대 {(total_result['completed'] + remaining) / total_result['total'] * 100:.1f}% 달성 가능")

def main():
    """초고속 동 정보 보완 실행"""
    print("⚡ 초고속 동 정보 보완 시스템")
    print("=" * 60)
    
    processor = FastDongCompletion()
    
    start_time = time.time()
    
    # 1단계: 대량 주소 파싱 (빠름)
    address_count = processor.batch_address_parsing(batch_size=10000)
    
    # 2단계: 스마트 지오코딩 (제한적)
    geo_count = processor.smart_geocoding_batch(limit=5000)
    
    # 3단계: 최종 보고서
    processor.final_completion_report()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n⚡ 처리 완료!")
    print(f"   주소 파싱: {address_count:,}개")
    print(f"   지오코딩: {geo_count:,}개")
    print(f"   총 처리: {address_count + geo_count:,}개")
    print(f"   소요 시간: {total_time:.1f}초")
    print(f"   처리 속도: {(address_count + geo_count) / total_time:.1f}개/초")

if __name__ == "__main__":
    main()
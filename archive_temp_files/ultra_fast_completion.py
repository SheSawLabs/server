#!/usr/bin/env python3
"""
Ultra Fast 동 정보 완성 시스템 - 남은 30K 데이터 처리
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

class UltraFastCompletion:
    """Ultra Fast 동 정보 완성"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.kakao_api_key = os.getenv('KAKAO_API_KEY', '')
        self.processed_count = 0
        self.geocoded_count = 0
        
    def process_in_chunks(self, chunk_size=2000):
        """청크 단위로 데이터 처리"""
        print(f"🚀 Ultra Fast 동 정보 완성 시작 (청크 크기: {chunk_size:,})")
        
        # 남은 데이터 수 확인
        count_query = """
        SELECT COUNT(*) as remaining
        FROM cctv_installations 
        WHERE (dong IS NULL OR dong = '')
        """
        
        remaining = self.db_manager.execute_query(count_query)[0]['remaining']
        print(f"   처리 대상: {remaining:,}개")
        
        if remaining == 0:
            print("   ✅ 처리할 데이터가 없습니다.")
            return
        
        total_processed = 0
        offset = 0
        
        while offset < remaining:
            actual_chunk_size = min(chunk_size, remaining - offset)
            
            print(f"\n📦 청크 {offset//chunk_size + 1}: {offset:,}~{offset + actual_chunk_size:,}")
            
            # 청크 데이터 가져오기
            chunk_query = """
            SELECT id, district, address, latitude, longitude
            FROM cctv_installations 
            WHERE (dong IS NULL OR dong = '')
            AND latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY district, id
            LIMIT %s OFFSET %s
            """
            
            chunk_data = self.db_manager.execute_query(chunk_query, (actual_chunk_size, offset))
            
            if not chunk_data:
                break
            
            # 청크 처리
            chunk_processed = self.process_chunk_geocoding(chunk_data)
            total_processed += chunk_processed
            
            print(f"   ✅ 청크 완료: {chunk_processed}/{len(chunk_data)}개")
            
            offset += actual_chunk_size
            
            # 진행 상황 출력
            if total_processed > 0:
                progress = (offset / remaining) * 100
                print(f"   📊 전체 진행: {offset:,}/{remaining:,} ({progress:.1f}%) - 처리: {total_processed:,}개")
        
        print(f"\n🎯 Ultra Fast 처리 완료: {total_processed:,}개")
        return total_processed
    
    def process_chunk_geocoding(self, chunk_data):
        """청크 단위 지오코딩 처리 (멀티스레딩)"""
        processed_count = 0
        
        # 스레드 풀로 병렬 처리 (API 제한 고려해서 최대 3개)
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_data = {
                executor.submit(self.geocode_single_record, record): record 
                for record in chunk_data
            }
            
            for future in as_completed(future_to_data):
                record = future_to_data[future]
                try:
                    dong_name = future.result()
                    if dong_name:
                        # DB 업데이트
                        update_query = """
                        UPDATE cctv_installations 
                        SET dong = %s, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                        """
                        self.db_manager.execute_non_query(update_query, (dong_name, record['id']))
                        processed_count += 1
                        
                except Exception as e:
                    continue
        
        return processed_count
    
    def geocode_single_record(self, record):
        """단일 레코드 지오코딩"""
        try:
            lat = float(record['latitude'])
            lng = float(record['longitude'])
            
            url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
            headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
            params = {"x": str(lng), "y": str(lat), "input_coord": "WGS84"}
            
            response = requests.get(url, headers=headers, params=params, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                if data['documents'] and data['documents'][0].get('address'):
                    region_3depth = data['documents'][0]['address'].get('region_3depth_name')
                    if region_3depth and '동' in region_3depth:
                        time.sleep(0.1)  # API 제한 준수
                        return region_3depth
            elif response.status_code == 429:
                time.sleep(1)  # API 제한시 대기
                
        except Exception:
            pass
        
        return None
    
    def final_status_check(self):
        """최종 상태 확인"""
        print(f"\n📋 최종 동 정보 완성도")
        print("=" * 50)
        
        # 전체 통계
        total_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM cctv_installations
        """
        
        result = self.db_manager.execute_query(total_query)[0]
        
        print(f"🎯 전체 현황:")
        print(f"   총 데이터: {result['total']:,}개")
        print(f"   완성된 데이터: {result['completed']:,}개")
        print(f"   남은 데이터: {result['total'] - result['completed']:,}개")
        print(f"   전체 완성도: {result['rate']}%")
        
        # 구별 완성도 (하위 10개)
        district_query = """
        SELECT 
            district,
            COUNT(*) as total,
            COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong IS NOT NULL AND dong <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM cctv_installations 
        GROUP BY district
        ORDER BY rate ASC, completed ASC
        LIMIT 10
        """
        
        district_results = self.db_manager.execute_query(district_query)
        
        print(f"\n⚠️ 완성도 낮은 구 순위:")
        for i, row in enumerate(district_results, 1):
            district = row['district']
            completed = row['completed']
            total = row['total']
            rate = row['rate']
            
            remaining = total - completed
            print(f"   {i:2d}. {district:8s}: {completed:4d}/{total:4d} ({rate:5.1f}%) - 남은 작업: {remaining:4d}개")

def main():
    """Ultra Fast 동 정보 완성 실행"""
    processor = UltraFastCompletion()
    
    start_time = time.time()
    
    # 청크 단위 처리 (2000개씩)
    total_processed = processor.process_in_chunks(chunk_size=2000)
    
    # 최종 상태 확인
    processor.final_status_check()
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"\n⚡ Ultra Fast 처리 완료!")
    print(f"   처리된 데이터: {total_processed:,}개")
    print(f"   소요 시간: {elapsed:.1f}초")
    if total_processed > 0:
        print(f"   처리 속도: {total_processed / elapsed:.1f}개/초")

if __name__ == "__main__":
    main()
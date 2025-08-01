#!/usr/bin/env python3
"""
경찰서 & 여성안심지킴이집 동 정보 보완 시스템
"""

import sys
import os
import re
import requests
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.db_connection import get_db_manager

class PoliceSafetyDongCompletion:
    """경찰서 & 여성안심지킴이집 동 정보 보완"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.kakao_api_key = os.getenv('KAKAO_API_KEY', '')
        
    def enhanced_address_parsing(self, address):
        """향상된 주소 파싱으로 동명 추출"""
        if not address:
            return None
        
        # 경찰서 특화 동명 추출 패턴들
        patterns = [
            # 괄호 안의 동명 (최우선)
            r'\(([가-힣]+\d*동)[,\s]*[^)]*\)',
            r'\(([^,]+),\s*([가-힣]+\d*동)\)',
            
            # 일반적인 동명 패턴들
            r'([가-힣]+\d*동)(?:[^\w가-힣]|$)',
            r'([가-힣]+\d*가동)(?:[^\w가-힣]|$)',
            r'([가-힣]+\d*로동)(?:[^\w가-힣]|$)',
            r'([가-힣]+\d*본동)(?:[^\w가-힣]|$)',
            r'([가-힣]+\d*신동)(?:[^\w가-힣]|$)',
            
            # 특수 패턴들
            r'(?:서울\s*)?[가-힣]+구\s*([가-힣]+\d*동)',
            
            # 도로명에서 동명 추출 시도
            r'([가-힣]+)로\d*길?\s*\d+',  # 도로명에서 동명 유추
        ]
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, address)
            for match in matches:
                # 튜플인 경우 (복수 그룹) 처리
                if isinstance(match, tuple):
                    for submatch in match:
                        if submatch and submatch.endswith('동'):
                            dong_name = submatch.strip()
                            if self._is_valid_dong(dong_name):
                                return dong_name
                else:
                    dong_name = match.strip()
                    
                    # 도로명 패턴인 경우 동명으로 변환 시도
                    if i == len(patterns) - 1:  # 마지막 패턴
                        dong_name = dong_name + '동'
                    
                    if self._is_valid_dong(dong_name):
                        return dong_name
        
        return None
    
    def _is_valid_dong(self, dong_name):
        """유효한 동명인지 검증"""
        if not dong_name or len(dong_name) < 2:
            return False
        
        if not dong_name.endswith('동'):
            return False
            
        # 제외할 패턴들
        exclude_patterns = ['건물동', '층동', '호동', '번동', '가동동']
        for pattern in exclude_patterns:
            if pattern in dong_name:
                return False
        
        # 너무 긴 동명 제외
        if len(dong_name) > 10:
            return False
            
        return True
    
    def forward_geocode_with_kakao(self, address):
        """카카오 API로 주소 -> 좌표 변환 후 역지오코딩"""
        if not address:
            return None
        
        # 1단계: 주소 -> 좌표
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
        params = {"query": address}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    doc = data['documents'][0]
                    lat = float(doc['y'])
                    lng = float(doc['x'])
                    
                    # 2단계: 좌표 -> 동정보
                    return self.reverse_geocode_with_kakao(lat, lng)
            elif response.status_code == 429:
                time.sleep(1)
                return self.forward_geocode_with_kakao(address)
                
        except Exception as e:
            pass
        
        return None
    
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
                if data['documents']:
                    doc = data['documents'][0]
                    if 'address' in doc:
                        region_3depth = doc['address'].get('region_3depth_name')
                        if region_3depth and '동' in region_3depth:
                            return region_3depth
            elif response.status_code == 429:
                time.sleep(1)  # API 제한시 대기
                return self.reverse_geocode_with_kakao(latitude, longitude)
                
        except Exception as e:
            pass
        
        return None
    
    def process_police_stations(self):
        """경찰서 동 정보 보완"""
        print("🚓 경찰서 동 정보 보완 시작...")
        
        # 동 정보가 없는 경찰서 데이터 조회
        query = """
        SELECT id, police_station_name, full_address, district_name, latitude, longitude
        FROM police_stations 
        WHERE dong_name IS NULL OR dong_name = ''
        ORDER BY district_name
        """
        
        results = self.db_manager.execute_query(query)
        total = len(results)
        
        print(f"   처리 대상: {total}개")
        
        if total == 0:
            print("   ✅ 처리할 경찰서 데이터가 없습니다.")
            return 0
        
        updated_count = 0
        
        for i, row in enumerate(results, 1):
            dong_name = None
            
            # 1단계: 주소 파싱
            if row['full_address']:
                dong_name = self.enhanced_address_parsing(row['full_address'])
            
            # 2단계: 역지오코딩 (좌표가 있는 경우)
            if not dong_name and row['latitude'] and row['longitude']:
                try:
                    dong_name = self.reverse_geocode_with_kakao(
                        float(row['latitude']), 
                        float(row['longitude'])
                    )
                    time.sleep(0.1)  # API 제한 준수
                except:
                    pass
            
            # 3단계: 순방향 지오코딩 (주소 -> 좌표 -> 동정보)
            if not dong_name and row['full_address']:
                try:
                    dong_name = self.forward_geocode_with_kakao(row['full_address'])
                    time.sleep(0.1)  # API 제한 준수
                except:
                    pass
            
            # 동 정보 업데이트
            if dong_name:
                update_query = """
                UPDATE police_stations 
                SET dong_name = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s
                """
                self.db_manager.execute_non_query(update_query, (dong_name, row['id']))
                updated_count += 1
                
                print(f"   {i:3d}. {row['police_station_name']} → {row['district_name']} {dong_name}")
            else:
                print(f"   {i:3d}. {row['police_station_name']} → 동 정보 없음")
            
            # 진행률 출력
            if i % 50 == 0 or i == total:
                print(f"       진행: {i}/{total} ({i/total*100:.1f}%) - 업데이트: {updated_count}개")
        
        print(f"   ✅ 경찰서 처리 완료: {updated_count}/{total}개")
        return updated_count
    
    def process_female_safety_houses(self):
        """여성안심지킴이집 동 정보 보완"""
        print(f"\n🏠 여성안심지킴이집 동 정보 보완 시작...")
        
        # 동 정보가 없는 여성안심지킴이집 데이터 조회
        query = """
        SELECT id, store_name, road_address, lot_address, district_name, latitude, longitude
        FROM female_safety_houses 
        WHERE dong_name IS NULL OR dong_name = ''
        ORDER BY district_name
        """
        
        results = self.db_manager.execute_query(query)
        total = len(results)
        
        print(f"   처리 대상: {total}개")
        
        if total == 0:
            print("   ✅ 처리할 여성안심지킴이집 데이터가 없습니다.")
            return 0
        
        updated_count = 0
        
        for i, row in enumerate(results, 1):
            dong_name = None
            
            # 1단계: 도로명 주소 파싱
            if row['road_address']:
                dong_name = self.enhanced_address_parsing(row['road_address'])
            
            # 2단계: 지번 주소 파싱 (도로명 주소 파싱 실패시)
            if not dong_name and row['lot_address']:
                dong_name = self.enhanced_address_parsing(row['lot_address'])
            
            # 3단계: 지오코딩 (주소 파싱 실패시)
            if not dong_name and row['latitude'] and row['longitude']:
                try:
                    dong_name = self.reverse_geocode_with_kakao(
                        float(row['latitude']), 
                        float(row['longitude'])
                    )
                    time.sleep(0.1)  # API 제한 준수
                except:
                    pass
            
            # 동 정보 업데이트
            if dong_name:
                update_query = """
                UPDATE female_safety_houses 
                SET dong_name = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s
                """
                self.db_manager.execute_non_query(update_query, (dong_name, row['id']))
                updated_count += 1
                
                print(f"   {i:3d}. {row['store_name']} → {row['district_name']} {dong_name}")
            else:
                print(f"   {i:3d}. {row['store_name']} → 동 정보 없음")
            
            # 진행률 출력
            if i % 50 == 0 or i == total:
                print(f"       진행: {i}/{total} ({i/total*100:.1f}%) - 업데이트: {updated_count}개")
        
        print(f"   ✅ 여성안심지킴이집 처리 완료: {updated_count}/{total}개")
        return updated_count
    
    def final_completion_report(self):
        """최종 완성도 보고서"""
        print(f"\n📋 경찰서 & 여성안심지킴이집 동 정보 완성도 보고서")
        print("=" * 60)
        
        # 경찰서 최종 통계
        police_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN dong_name IS NOT NULL AND dong_name <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong_name IS NOT NULL AND dong_name <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM police_stations
        """
        
        police_result = self.db_manager.execute_query(police_query)[0]
        
        print(f"🚓 경찰서 최종 현황:")
        print(f"   총 데이터: {police_result['total']:,}개")
        print(f"   완성된 데이터: {police_result['completed']:,}개")
        print(f"   완성도: {police_result['rate']}%")
        
        # 여성안심지킴이집 최종 통계
        safety_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN dong_name IS NOT NULL AND dong_name <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong_name IS NOT NULL AND dong_name <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM female_safety_houses
        """
        
        safety_result = self.db_manager.execute_query(safety_query)[0]
        
        print(f"\n🏠 여성안심지킴이집 최종 현황:")
        print(f"   총 데이터: {safety_result['total']:,}개")
        print(f"   완성된 데이터: {safety_result['completed']:,}개")
        print(f"   완성도: {safety_result['rate']}%")
        
        # 구별 완성도 (상위 10개)
        district_query = """
        SELECT 
            district_name,
            COUNT(*) as total,
            COUNT(CASE WHEN dong_name IS NOT NULL AND dong_name <> '' THEN 1 END) as completed,
            ROUND(COUNT(CASE WHEN dong_name IS NOT NULL AND dong_name <> '' THEN 1 END) * 100.0 / COUNT(*), 1) as rate
        FROM (
            SELECT district_name, dong_name FROM police_stations
            UNION ALL
            SELECT district_name, dong_name FROM female_safety_houses
        ) combined
        GROUP BY district_name
        ORDER BY rate DESC, completed DESC
        LIMIT 10
        """
        
        district_results = self.db_manager.execute_query(district_query)
        
        print(f"\n🏆 구별 완성도 순위 (상위 10개):")
        for i, row in enumerate(district_results, 1):
            district = row['district_name']
            completed = row['completed']
            total = row['total']
            rate = row['rate']
            
            print(f"   {i:2d}. {district:8s}: {completed:3d}/{total:3d} ({rate:5.1f}%)")

def main():
    """경찰서 & 여성안심지킴이집 동 정보 보완 실행"""
    print("🚀 경찰서 & 여성안심지킴이집 동 정보 보완 시스템")
    print("=" * 60)
    
    processor = PoliceSafetyDongCompletion()
    
    start_time = time.time()
    
    # 1. 경찰서 처리
    police_updated = processor.process_police_stations()
    
    # 2. 여성안심지킴이집 처리
    safety_updated = processor.process_female_safety_houses()
    
    # 3. 최종 보고서
    processor.final_completion_report()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n⚡ 처리 완료!")
    print(f"   경찰서: {police_updated:,}개")
    print(f"   여성안심지킴이집: {safety_updated:,}개")
    print(f"   총 처리: {police_updated + safety_updated:,}개")
    print(f"   소요 시간: {total_time:.1f}초")

if __name__ == "__main__":
    main()
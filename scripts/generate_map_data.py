#!/usr/bin/env python3
"""
동별 요약 데이터 JSON 생성 스크립트 (map_data.json)
- 동 코드, 구, 동 이름
- 등급(grade), 총점(score)
- 좌표(lat, lng) - 지도 표시용
- 주요 지표 개수 (CCTV, 안심이집 등)
"""

import json
import sys
import os
from typing import Dict, List, Any
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db.db_connection import get_db_manager

class MapDataGenerator:
    """지도용 동별 요약 데이터 생성기"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
    
    def get_dong_coordinates(self, district: str, dong: str) -> tuple:
        """
        동별 대표 좌표 계산 (CCTV 설치 위치의 중심점)
        """
        try:
            query = """
                SELECT 
                    AVG(CAST(latitude AS FLOAT)) as avg_lat,
                    AVG(CAST(longitude AS FLOAT)) as avg_lng
                FROM cctv_installations 
                WHERE district = %s AND dong = %s
                  AND latitude IS NOT NULL AND longitude IS NOT NULL
                  AND latitude != '' AND longitude != ''
                  AND CAST(latitude AS FLOAT) BETWEEN 37.0 AND 38.0
                  AND CAST(longitude AS FLOAT) BETWEEN 126.0 AND 128.0
            """
            
            result = self.db_manager.execute_query(query, (district, dong))
            
            if result and result[0]['avg_lat'] and result[0]['avg_lng']:
                return round(float(result[0]['avg_lat']), 6), round(float(result[0]['avg_lng']), 6)
            
            # CCTV 데이터가 없으면 서울 중심부 좌표 반환 (구별로 약간 다르게)
            district_coords = {
                '강남구': (37.5173, 127.0473),
                '강동구': (37.5301, 127.1238),
                '강북구': (37.6394, 127.0248),
                '강서구': (37.5509, 126.8495),
                '관악구': (37.4782, 126.9516),
                '광진구': (37.5385, 127.0823),
                '구로구': (37.4955, 126.8874),
                '금천구': (37.4569, 126.8956),
                '노원구': (37.6542, 127.0568),
                '도봉구': (37.6689, 127.0471),
                '동대문구': (37.5744, 127.0398),
                '동작구': (37.5124, 126.9393),
                '마포구': (37.5663, 126.9019),
                '서대문구': (37.5791, 126.9368),
                '서초구': (37.4837, 127.0324),
                '성동구': (37.5636, 127.0369),
                '성북구': (37.5894, 127.0167),
                '송파구': (37.5146, 127.1059),
                '양천구': (37.5170, 126.8664),
                '영등포구': (37.5264, 126.8962),
                '용산구': (37.5324, 126.9910),
                '은평구': (37.6027, 126.9291),
                '종로구': (37.5735, 126.9788),
                '중구': (37.5641, 126.9979),
                '중랑구': (37.6063, 127.0925)
            }
            
            return district_coords.get(district, (37.5665, 126.9780))  # 서울시청 좌표
            
        except Exception as e:
            print(f"좌표 조회 오류 ({district} {dong}): {e}")
            return (37.5665, 126.9780)  # 기본값: 서울시청
    
    def generate_map_data(self) -> List[Dict[str, Any]]:
        """
        지도용 동별 요약 데이터 생성
        
        Returns:
            동별 요약 데이터 리스트
        """
        try:
            # 동별 안전도 데이터 조회
            query = """
                SELECT 
                    district,
                    dong,
                    total_score,
                    safety_grade,
                    cctv_count,
                    streetlight_count,
                    police_station_count,
                    female_safety_house_count,
                    sexual_offender_count,
                    delivery_box_count
                FROM dong_safety_scores
                ORDER BY district, dong
            """
            
            results = self.db_manager.execute_query(query)
            
            map_data = []
            
            print(f"🗺️ {len(results)}개 동의 지도 데이터 생성 중...")
            
            for i, row in enumerate(results, 1):
                district = row['district']
                dong = row['dong']
                
                # 동별 좌표 계산
                lat, lng = self.get_dong_coordinates(district, dong)
                
                # 동 코드 생성 (구코드 + 동순번)
                dong_code = f"{hash(f'{district}_{dong}') % 100000:05d}"
                
                dong_data = {
                    "dong_code": dong_code,
                    "district": district,
                    "dong": dong,
                    "grade": row['safety_grade'],
                    "score": float(row['total_score']),
                    "coordinates": {
                        "lat": lat,
                        "lng": lng
                    },
                    "facilities": {
                        "cctv": int(row['cctv_count']),
                        "streetlight": int(row['streetlight_count']),
                        "police_station": int(row['police_station_count']),
                        "safety_house": int(row['female_safety_house_count']),
                        "delivery_box": int(row['delivery_box_count'])
                    },
                    "risk_factors": {
                        "sexual_offender": int(row['sexual_offender_count'])
                    }
                }
                
                map_data.append(dong_data)
                
                # 진행률 표시
                if i % 50 == 0 or i == len(results):
                    print(f"📍 진행률: {i}/{len(results)} ({(i/len(results)*100):.1f}%)")
            
            return map_data
            
        except Exception as e:
            print(f"❌ 지도 데이터 생성 오류: {e}")
            return []
    
    def save_to_json(self, data: List[Dict[str, Any]], filename: str = "map_data.json"):
        """JSON 파일로 저장"""
        try:
            # 메타데이터 추가
            output_data = {
                "metadata": {
                    "title": "서울시 동별 안전도 지도 데이터",
                    "description": "동별 안전도 등급, 점수, 좌표 및 주요 시설 개수 정보",
                    "generated_at": datetime.now().isoformat(),
                    "total_dong": len(data),
                    "grade_distribution": {}
                },
                "data": data
            }
            
            # 등급별 분포 계산
            for item in data:
                grade = item['grade']
                output_data["metadata"]["grade_distribution"][grade] = \
                    output_data["metadata"]["grade_distribution"].get(grade, 0) + 1
            
            # JSON 파일 저장
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 지도 데이터 저장 완료: {filename}")
            print(f"   총 동 수: {len(data)}개")
            print(f"   등급별 분포: {output_data['metadata']['grade_distribution']}")
            
            return filename
            
        except Exception as e:
            print(f"❌ JSON 저장 오류: {e}")
            return None


def main():
    """메인 실행"""
    print("🗺️ 서울시 동별 지도 데이터 생성 시작")
    print("=" * 50)
    
    generator = MapDataGenerator()
    
    # 지도 데이터 생성
    map_data = generator.generate_map_data()
    
    if not map_data:
        print("❌ 데이터 생성 실패")
        return
    
    # JSON 파일 저장
    filename = generator.save_to_json(map_data)
    
    if filename:
        print(f"\n🎯 생성 완료!")
        print(f"   파일: {filename}")
        print(f"   크기: {os.path.getsize(filename) / 1024:.1f} KB")
        
        # 샘플 데이터 출력
        print(f"\n📋 샘플 데이터:")
        for i, sample in enumerate(map_data[:3]):
            print(f"   {i+1}. {sample['district']} {sample['dong']}: "
                  f"{sample['score']}점 ({sample['grade']}등급) "
                  f"@ ({sample['coordinates']['lat']}, {sample['coordinates']['lng']})")


if __name__ == "__main__":
    main()
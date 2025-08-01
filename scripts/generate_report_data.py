#!/usr/bin/env python3
"""
동별 상세 리포트 JSON 생성 스크립트 (report_data.json)
- 위 요약 정보 + 지표별 세부 수치 (밀도, 기준치 등)
- 기준치 텍스트 포함
"""

import json
import sys
import os
from typing import Dict, List, Any
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db.db_connection import get_db_manager

class ReportDataGenerator:
    """동별 상세 리포트 데이터 생성기"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        
        # CPTED 기준치 정의
        self.standards = {
            "cctv": {
                "recommended_per_km2": 30,
                "description": "CCTV 30대/㎢ 이상 권장 (범죄예방 효과)"
            },
            "streetlight": {
                "recommended_per_km2": 100,
                "description": "가로등 100개/㎢ 이상 권장 (야간 조명 확보)"
            },
            "police_station": {
                "recommended_per_km2": 1,
                "description": "경찰서 1개소/㎢ 이상 권장 (신속한 대응)"
            },
            "safety_house": {
                "recommended_per_km2": 10,
                "description": "여성안심지킴이집 10개소/㎢ 이상 권장 (긴급 피난처)"
            },
            "delivery_box": {
                "recommended_per_km2": 15,
                "description": "안심택배함 15개/㎢ 이상 권장 (배송 보안)"
            },
            "sexual_offender": {
                "recommended_per_km2": 0,
                "description": "성범죄자 0명/㎢ 목표 (위험 요소 최소화)"
            }
        }
        
        # CPTED 영역별 설명
        self.cpted_descriptions = {
            "natural_surveillance": {
                "name": "자연적 감시",
                "weight": "35%",
                "description": "CCTV, 가로등 등을 통한 자연스러운 감시 환경 조성",
                "factors": ["CCTV 설치", "가로등 조명", "시야 확보"]
            },
            "access_control": {
                "name": "접근 통제",
                "weight": "25%", 
                "description": "성범죄자 등 위험 요소 통제 및 관리",
                "factors": ["성범죄자 관리", "출입 통제", "위험 지역 차단"]
            },
            "territoriality": {
                "name": "영역성 강화",
                "weight": "20%",
                "description": "경찰서, 안심지킴이집 등 공식적 관리 체계",
                "factors": ["경찰서 배치", "안심지킴이집", "공공시설 관리"]
            },
            "maintenance": {
                "name": "유지관리",
                "weight": "10%",
                "description": "시설 및 환경의 지속적 관리 상태",
                "factors": ["시설 정비", "환경 정리", "파손 수리"]
            },
            "activity_support": {
                "name": "활동성 지원",
                "weight": "10%",
                "description": "안심택배함 등 일상 활동 지원 시설",
                "factors": ["택배 보안", "상권 활성화", "유동인구 증대"]
            }
        }
    
    def get_dong_coordinates(self, district: str, dong: str) -> tuple:
        """동별 대표 좌표 계산"""
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
            
            # 기본 좌표 (구별)
            district_coords = {
                '강남구': (37.5173, 127.0473), '강동구': (37.5301, 127.1238),
                '강북구': (37.6394, 127.0248), '강서구': (37.5509, 126.8495),
                '관악구': (37.4782, 126.9516), '광진구': (37.5385, 127.0823),
                '구로구': (37.4955, 126.8874), '금천구': (37.4569, 126.8956),
                '노원구': (37.6542, 127.0568), '도봉구': (37.6689, 127.0471),
                '동대문구': (37.5744, 127.0398), '동작구': (37.5124, 126.9393),
                '마포구': (37.5663, 126.9019), '서대문구': (37.5791, 126.9368),
                '서초구': (37.4837, 127.0324), '성동구': (37.5636, 127.0369),
                '성북구': (37.5894, 127.0167), '송파구': (37.5146, 127.1059),
                '양천구': (37.5170, 126.8664), '영등포구': (37.5264, 126.8962),
                '용산구': (37.5324, 126.9910), '은평구': (37.6027, 126.9291),
                '종로구': (37.5735, 126.9788), '중구': (37.5641, 126.9979),
                '중랑구': (37.6063, 127.0925)
            }
            
            return district_coords.get(district, (37.5665, 126.9780))
            
        except Exception as e:
            return (37.5665, 126.9780)
    
    def calculate_facility_analysis(self, count: int, area_size: float, standard: Dict) -> Dict:
        """시설별 분석 데이터 계산"""
        density = count / area_size if area_size > 0 else 0
        recommended = standard["recommended_per_km2"]
        
        # 충족도 계산
        if recommended == 0:  # 성범죄자의 경우 (적을수록 좋음)
            adequacy = max(0, 100 - (density * 20))  # 1명당 -20점
            status = "양호" if density == 0 else "위험" if density >= 5 else "주의"
        else:
            adequacy = min(100, (density / recommended) * 100)
            if adequacy >= 80:
                status = "충족"
            elif adequacy >= 50:
                status = "보통"
            else:
                status = "부족"
        
        return {
            "count": count,
            "density": round(density, 2),
            "recommended": recommended,
            "adequacy": round(adequacy, 1),
            "status": status,
            "description": standard["description"]
        }
    
    def generate_report_data(self) -> List[Dict[str, Any]]:
        """동별 상세 리포트 데이터 생성"""
        try:
            # 동별 안전도 데이터 조회
            query = """
                SELECT 
                    district, dong, total_score, safety_grade,
                    natural_surveillance, access_control, territoriality, 
                    maintenance, activity_support,
                    cctv_count, streetlight_count, police_station_count,
                    female_safety_house_count, sexual_offender_count, 
                    delivery_box_count, area_size
                FROM dong_safety_scores
                ORDER BY district, dong
            """
            
            results = self.db_manager.execute_query(query)
            report_data = []
            
            print(f"📊 {len(results)}개 동의 상세 리포트 생성 중...")
            
            for i, row in enumerate(results, 1):
                district = row['district']
                dong = row['dong']
                area_size = float(row['area_size'])
                
                # 좌표 계산
                lat, lng = self.get_dong_coordinates(district, dong)
                
                # 동 코드 생성
                dong_code = f"{hash(f'{district}_{dong}') % 100000:05d}"
                
                # 시설별 분석
                facility_analysis = {
                    "cctv": self.calculate_facility_analysis(
                        int(row['cctv_count']), area_size, self.standards["cctv"]
                    ),
                    "streetlight": self.calculate_facility_analysis(
                        int(row['streetlight_count']), area_size, self.standards["streetlight"]
                    ),
                    "police_station": self.calculate_facility_analysis(
                        int(row['police_station_count']), area_size, self.standards["police_station"]
                    ),
                    "safety_house": self.calculate_facility_analysis(
                        int(row['female_safety_house_count']), area_size, self.standards["safety_house"]
                    ),
                    "delivery_box": self.calculate_facility_analysis(
                        int(row['delivery_box_count']), area_size, self.standards["delivery_box"]
                    ),
                    "sexual_offender": self.calculate_facility_analysis(
                        int(row['sexual_offender_count']), area_size, self.standards["sexual_offender"]
                    )
                }
                
                # CPTED 점수 분석
                cpted_analysis = {
                    "natural_surveillance": {
                        "score": float(row['natural_surveillance']),
                        "weight": "35%",
                        "description": self.cpted_descriptions["natural_surveillance"]["description"],
                        "factors": self.cpted_descriptions["natural_surveillance"]["factors"]
                    },
                    "access_control": {
                        "score": float(row['access_control']),
                        "weight": "25%",
                        "description": self.cpted_descriptions["access_control"]["description"],
                        "factors": self.cpted_descriptions["access_control"]["factors"]
                    },
                    "territoriality": {
                        "score": float(row['territoriality']),
                        "weight": "20%",
                        "description": self.cpted_descriptions["territoriality"]["description"],
                        "factors": self.cpted_descriptions["territoriality"]["factors"]
                    },
                    "maintenance": {
                        "score": float(row['maintenance']),
                        "weight": "10%",
                        "description": self.cpted_descriptions["maintenance"]["description"],
                        "factors": self.cpted_descriptions["maintenance"]["factors"]
                    },
                    "activity_support": {
                        "score": float(row['activity_support']),
                        "weight": "10%",
                        "description": self.cpted_descriptions["activity_support"]["description"],
                        "factors": self.cpted_descriptions["activity_support"]["factors"]
                    }
                }
                
                # 개선 권고사항 생성
                recommendations = []
                
                if facility_analysis["cctv"]["adequacy"] < 50:
                    recommendations.append("CCTV 설치 확대 필요 (범죄 예방 강화)")
                
                if facility_analysis["streetlight"]["adequacy"] < 50:
                    recommendations.append("가로등 조명 개선 필요 (야간 안전성 향상)")
                
                if facility_analysis["safety_house"]["adequacy"] < 50:
                    recommendations.append("여성안심지킴이집 확충 필요 (긴급상황 대응)")
                
                if facility_analysis["sexual_offender"]["adequacy"] < 80:
                    recommendations.append("성범죄자 관리 강화 필요 (위험 요소 제거)")
                
                if not recommendations:
                    recommendations.append("현재 안전 시설이 잘 갖춰져 있습니다")
                
                dong_report = {
                    "dong_code": dong_code,
                    "district": district,
                    "dong": dong,
                    "summary": {
                        "grade": row['safety_grade'],
                        "score": float(row['total_score']),
                        "area_size": area_size,
                        "coordinates": {"lat": lat, "lng": lng}
                    },
                    "cpted_analysis": cpted_analysis,
                    "facility_analysis": facility_analysis,
                    "recommendations": recommendations,
                    "generated_at": datetime.now().isoformat()
                }
                
                report_data.append(dong_report)
                
                # 진행률 표시
                if i % 50 == 0 or i == len(results):
                    print(f"📈 진행률: {i}/{len(results)} ({(i/len(results)*100):.1f}%)")
            
            return report_data
            
        except Exception as e:
            print(f"❌ 리포트 데이터 생성 오류: {e}")
            return []
    
    def save_to_json(self, data: List[Dict[str, Any]], filename: str = "report_data.json"):
        """JSON 파일로 저장"""
        try:
            # 메타데이터 추가
            output_data = {
                "metadata": {
                    "title": "서울시 동별 안전도 상세 리포트",
                    "description": "동별 CPTED 기반 안전도 분석 및 시설 현황 상세 정보",
                    "generated_at": datetime.now().isoformat(),
                    "total_dong": len(data),
                    "cpted_principles": self.cpted_descriptions,
                    "facility_standards": self.standards
                },
                "reports": data
            }
            
            # JSON 파일 저장
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 상세 리포트 저장 완료: {filename}")
            print(f"   총 동 수: {len(data)}개")
            
            return filename
            
        except Exception as e:
            print(f"❌ JSON 저장 오류: {e}")
            return None


def main():
    """메인 실행"""
    print("📊 서울시 동별 상세 리포트 데이터 생성 시작")
    print("=" * 60)
    
    generator = ReportDataGenerator()
    
    # 상세 리포트 데이터 생성
    report_data = generator.generate_report_data()
    
    if not report_data:
        print("❌ 데이터 생성 실패")
        return
    
    # JSON 파일 저장
    filename = generator.save_to_json(report_data)
    
    if filename:
        print(f"\n🎯 생성 완료!")
        print(f"   파일: {filename}")
        print(f"   크기: {os.path.getsize(filename) / 1024:.1f} KB")
        
        # 샘플 데이터 출력
        print(f"\n📋 샘플 리포트:")
        sample = report_data[0]
        print(f"   동명: {sample['district']} {sample['dong']}")
        print(f"   등급: {sample['summary']['grade']} ({sample['summary']['score']}점)")
        print(f"   면적: {sample['summary']['area_size']}㎢")
        print(f"   CCTV 밀도: {sample['facility_analysis']['cctv']['density']}대/㎢")
        print(f"   권고사항: {len(sample['recommendations'])}건")


if __name__ == "__main__":
    main()
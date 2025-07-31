#!/usr/bin/env python3
"""
Detailed Report Generator - 동별 상세 안전도 분석 리포트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety_score.cpted_calculator import CPTEDCalculator


class DetailedSafetyReportGenerator:
    """상세 안전도 리포트 생성 클래스"""
    
    def __init__(self):
        self.calculator = CPTEDCalculator()
        
        # 등급별 설명
        self.grade_descriptions = {
            'A': '매우 안전 - 종합적인 안전 인프라가 우수함',
            'B': '안전 - 대부분의 안전 요소가 양호함',
            'C': '보통 - 일부 안전 요소 개선 필요',
            'D': '위험 - 안전 인프라 보강이 시급함',
            'E': '매우 위험 - 전반적인 안전 대책 마련 필요'
        }
    
    def generate_dong_detailed_report(self, safety_score_data):
        """동별 상세 리포트 생성"""
        
        district = safety_score_data['district']
        dong = safety_score_data['dong']
        total_score = safety_score_data['total_score']
        grade = safety_score_data['grade']
        
        print(f"\n" + "="*80)
        print(f"🏘️  {district} {dong} 상세 안전도 분석 리포트")
        print(f"="*80)
        
        # 종합 점수 및 등급
        print(f"\n📊 종합 안전도: {total_score:.1f}점 ({grade}등급)")
        print(f"    등급 설명: {self.grade_descriptions[grade]}")
        
        # CPTED 원칙별 상세 분석
        self._analyze_natural_surveillance(safety_score_data)
        self._analyze_access_control(safety_score_data)
        self._analyze_territoriality(safety_score_data)
        self._analyze_maintenance(safety_score_data)
        self._analyze_activity_support(safety_score_data)
        
        # 개선 권고사항
        self._generate_improvement_recommendations(safety_score_data)
    
    def _analyze_natural_surveillance(self, data):
        """자연적 감시 분석"""
        score = data['natural_surveillance']
        cctv_count = data['cctv_count']
        streetlight_count = data['streetlight_count']
        
        print(f"\n🔍 1. 자연적 감시 (가중치 35%): {score:.1f}점")
        print(f"    - CCTV 설치 현황: {cctv_count}개")
        print(f"    - 가로등 설치 현황: {streetlight_count}개")
        
        # 점수 분석
        if score >= 80:
            print(f"    ✅ 우수: CCTV와 가로등이 충분히 설치되어 자연적 감시 환경이 우수합니다")
        elif score >= 60:
            print(f"    🟡 양호: 자연적 감시 환경이 양호하나 일부 개선 여지가 있습니다")
        elif score >= 40:
            print(f"    🟠 보통: CCTV 또는 가로등 추가 설치가 필요합니다")
        else:
            print(f"    🔴 미흡: 자연적 감시를 위한 CCTV와 가로등 설치가 시급합니다")
        
        # 상세 계산 설명
        area_size = 2.4  # 서울 평균 동 면적
        cctv_density = cctv_count / area_size
        streetlight_density = streetlight_count / area_size
        
        print(f"    📈 계산 근거:")
        print(f"       - CCTV 밀도: {cctv_density:.1f}개/km² (기준: 50개/km²=100점)")
        print(f"       - 가로등 밀도: {streetlight_density:.1f}개/km² (기준: 1000개/km²=100점)")
        print(f"       - 가중치: CCTV 70% + 가로등 30%")
    
    def _analyze_access_control(self, data):
        """접근통제 분석"""
        score = data['access_control']
        offender_count = data['sexual_offender_count']
        
        print(f"\n🚪 2. 접근통제 (가중치 25%): {score:.1f}점")
        print(f"    - 성범죄자 거주 현황: {offender_count}명")
        
        # 점수 분석
        if score >= 90:
            print(f"    ✅ 우수: 성범죄자 거주 밀도가 매우 낮아 접근통제가 우수합니다")
        elif score >= 70:
            print(f"    🟡 양호: 성범죄자 거주 밀도가 낮은 편입니다")
        elif score >= 50:
            print(f"    🟠 보통: 성범죄자 거주 현황에 주의가 필요합니다")
        else:
            print(f"    🔴 미흡: 성범죄자 거주 밀도가 높아 각별한 주의가 필요합니다")
        
        # 상세 계산 설명
        area_size = 2.4
        offender_density = offender_count / area_size
        
        print(f"    📈 계산 근거:")
        print(f"       - 성범죄자 밀도: {offender_density:.1f}명/km²")
        print(f"       - 계산 공식: 100 × exp(-밀도/10) (밀도가 높을수록 점수 감소)")
        print(f"       - 0명/km² = 100점, 10명/km² ≈ 37점")
    
    def _analyze_territoriality(self, data):
        """영역성 강화 분석"""
        score = data['territoriality']
        police_count = data['police_station_count']
        safety_house_count = data['female_safety_house_count']
        
        print(f"\n🏛️  3. 영역성 강화 (가중치 20%): {score:.1f}점")
        print(f"    - 경찰서/파출소 현황: {police_count}개")
        print(f"    - 여성안심지킴이집 현황: {safety_house_count}개")
        
        # 점수 분석
        if score >= 80:
            print(f"    ✅ 우수: 치안 시설과 안심 시설이 충분하여 영역성이 우수합니다")
        elif score >= 60:
            print(f"    🟡 양호: 영역성 강화 시설이 양호한 수준입니다")
        elif score >= 40:
            print(f"    🟠 보통: 치안 시설 또는 안심 시설 확충이 필요합니다")
        else:
            print(f"    🔴 미흡: 영역성 강화를 위한 시설 확충이 시급합니다")
        
        # 상세 계산 설명
        area_size = 2.4
        police_density = police_count / area_size
        safety_house_density = safety_house_count / area_size
        
        print(f"    📈 계산 근거:")
        print(f"       - 경찰서 밀도: {police_density:.1f}개/km² (기준: 5개/km²=100점)")
        print(f"       - 안심지킴이집 밀도: {safety_house_density:.1f}개/km² (기준: 20개/km²=100점)")
        print(f"       - 가중치: 경찰서 70% + 안심지킴이집 30%")
    
    def _analyze_maintenance(self, data):
        """유지관리 분석"""
        score = data['maintenance']
        
        print(f"\n🔧 4. 유지관리 (가중치 10%): {score:.1f}점")
        print(f"    - 현재 기본값 사용 중 (60점)")
        
        # 점수 분석
        if score >= 80:
            print(f"    ✅ 우수: 지역 환경 유지관리가 우수합니다")
        elif score >= 60:
            print(f"    🟡 양호: 지역 환경 유지관리가 양호합니다")
        else:
            print(f"    🟠 보통: 지역 환경 유지관리 개선이 필요합니다")
        
        print(f"    📝 참고:")
        print(f"       - 향후 실제 데이터 연동 예정 (어두운 골목, 쓰레기 방치 등)")
        print(f"       - 현재는 서울시 평균 수준으로 가정")
    
    def _analyze_activity_support(self, data):
        """활동성 분석"""
        score = data['activity_support']
        delivery_count = data['delivery_box_count']
        
        print(f"\n🏃 5. 활동성 (가중치 10%): {score:.1f}점")
        print(f"    - 안심택배함 현황: {delivery_count}개")
        print(f"    - 기본 활동성 점수: 70점 (서울시 평균)")
        
        # 점수 분석
        if score >= 80:
            print(f"    ✅ 우수: 주민 활동을 지원하는 시설이 우수합니다")
        elif score >= 60:
            print(f"    🟡 양호: 활동성 지원 시설이 양호합니다")
        else:
            print(f"    🟠 보통: 주민 활동성 증진을 위한 시설 확충이 필요합니다")
        
        # 상세 계산 설명
        area_size = 2.4
        delivery_density = delivery_count / area_size
        
        print(f"    📈 계산 근거:")
        print(f"       - 안심택배함 밀도: {delivery_density:.1f}개/km² (기준: 10개/km²=100점)")
        print(f"       - 가중치: 안심택배함 30% + 기본 활동성 70%")
        print(f"       - 향후 유동인구, 상권 데이터 연동 예정")
    
    def _generate_improvement_recommendations(self, data):
        """개선 권고사항 생성"""
        print(f"\n💡 개선 권고사항")
        print(f"="*50)
        
        recommendations = []
        
        # 자연적 감시 개선
        if data['natural_surveillance'] < 60:
            if data['cctv_count'] < 50:
                recommendations.append("🔍 CCTV 추가 설치를 통한 감시 영역 확대")
            if data['streetlight_count'] < 1000:
                recommendations.append("💡 가로등 증설을 통한 야간 조명 개선")
        
        # 접근통제 개선
        if data['access_control'] < 70:
            recommendations.append("🚨 성범죄자 알림 서비스 강화 및 주민 인식 제고")
            recommendations.append("📱 안전 신고 앱 보급 및 활용도 증진")
        
        # 영역성 강화
        if data['territoriality'] < 60:
            if data['police_station_count'] == 0:
                recommendations.append("👮 지구대/파출소 신설 또는 순찰 강화")
            if data['female_safety_house_count'] < 10:
                recommendations.append("🏠 여성안심지킴이집 확대 운영")
        
        # 유지관리 개선
        if data['maintenance'] < 60:
            recommendations.append("🔧 어두운 골목 조명 개선 및 환경 정비")
            recommendations.append("🗑️ 쓰레기 불법투기 단속 및 청소 강화")
        
        # 활동성 개선
        if data['activity_support'] < 60:
            if data['delivery_box_count'] < 5:
                recommendations.append("📦 안심택배함 추가 설치")
            recommendations.append("🎪 주민 참여형 안전 프로그램 운영")
            recommendations.append("🏪 야간 운영 상점 확대를 통한 자연적 감시 증진")
        
        # 종합 등급별 권고사항
        grade = data['grade']
        if grade in ['D', 'E']:
            recommendations.append("⚠️ 종합적인 안전 마스터플랜 수립 필요")
            recommendations.append("🚨 우선순위 시설 집중 투자")
        elif grade == 'C':
            recommendations.append("📈 약점 영역 집중 개선을 통한 단계적 안전도 향상")
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i:2d}. {rec}")
        else:
            print("   ✅ 현재 안전도가 양호한 수준으로 유지 관리에 집중하시기 바랍니다.")
        
        print()
    
    def generate_multiple_dong_comparison(self, safety_scores_list, comparison_type="district"):
        """여러 동 비교 리포트 생성"""
        
        if not safety_scores_list:
            return
        
        print(f"\n" + "="*100)
        print(f"📊 다중 지역 안전도 비교 분석")
        print(f"="*100)
        
        if comparison_type == "district":
            # 구별 비교
            from collections import defaultdict
            district_data = defaultdict(list)
            
            for score in safety_scores_list:
                district_data[score['district']].append(score)
            
            print(f"\n🏛️  구별 안전도 비교:")
            print(f"{'구명':<10} {'평균점수':<8} {'등급분포':<20} {'동수':<6}")
            print("-" * 60)
            
            for district, scores in district_data.items():
                avg_score = sum(s['total_score'] for s in scores) / len(scores)
                grade_count = {}
                for score in scores:
                    grade = score['grade']
                    grade_count[grade] = grade_count.get(grade, 0) + 1
                
                grade_str = " ".join([f"{g}:{c}" for g, c in sorted(grade_count.items())])
                print(f"{district:<10} {avg_score:>6.1f}점   {grade_str:<20} {len(scores):>4}개")
        
        # 상위/하위 지역 상세 분석
        sorted_scores = sorted(safety_scores_list, key=lambda x: x['total_score'], reverse=True)
        
        print(f"\n🏆 최고 안전도 지역 상세 분석:")
        self.generate_dong_detailed_report(sorted_scores[0])
        
        print(f"\n⚠️  최저 안전도 지역 상세 분석:")
        self.generate_dong_detailed_report(sorted_scores[-1])
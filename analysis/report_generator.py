#!/usr/bin/env python3
"""
Report Generator - 안전도 분석 보고서 생성
"""

from collections import defaultdict


class SafetyReportGenerator:
    """안전도 분석 보고서 생성 클래스"""
    
    def __init__(self):
        pass
    
    def generate_comprehensive_report(self, safety_scores):
        """종합 안전도 분석 보고서 생성"""
        
        if not safety_scores:
            print("❌ 분석할 데이터가 없습니다.")
            return
        
        print(f"\n🔒 서울시 종합 안전도 분석 결과")
        print("=" * 60)
        
        # 등급별 분포
        self._print_grade_distribution(safety_scores)
        
        # 상위 15개 동
        self._print_top_dong(safety_scores)
        
        # 하위 15개 동
        self._print_bottom_dong(safety_scores)
        
        # 구별 평균 안전도
        self._print_district_averages(safety_scores)
        
        # CPTED 원칙별 평균 점수
        self._print_cpted_averages(safety_scores)
    
    def _print_grade_distribution(self, safety_scores):
        """등급별 분포 출력"""
        grade_dist = defaultdict(int)
        for score in safety_scores:
            grade_dist[score['grade']] += 1
        
        print(f"\n📈 등급별 분포 (총 {len(safety_scores)}개 동):")
        for grade in ['A', 'B', 'C', 'D', 'E']:
            count = grade_dist[grade]
            percentage = (count / len(safety_scores) * 100) if safety_scores else 0
            print(f"   {grade}등급: {count:3d}개 ({percentage:5.1f}%)")
    
    def _print_top_dong(self, safety_scores):
        """상위 15개 동 출력"""
        top_15 = sorted(safety_scores, key=lambda x: x['total_score'], reverse=True)[:15]
        print(f"\n🏆 안전도 상위 15개 동:")
        for i, score in enumerate(top_15, 1):
            print(f"   {i:2d}. {score['district']} {score['dong']}: {score['total_score']:.1f}점 ({score['grade']}등급)")
            if i <= 3:  # 상위 3개는 상세 정보 표시
                print(f"       CCTV: {score['cctv_count']}개, 가로등: {score['streetlight_count']}개")
                print(f"       경찰서: {score['police_station_count']}개, 여성안심지킴이집: {score['female_safety_house_count']}개")
    
    def _print_bottom_dong(self, safety_scores):
        """하위 15개 동 출력"""
        bottom_15 = sorted(safety_scores, key=lambda x: x['total_score'])[:15]
        print(f"\n⚠️  안전도 하위 15개 동:")
        for i, score in enumerate(bottom_15, 1):
            print(f"   {i:2d}. {score['district']} {score['dong']}: {score['total_score']:.1f}점 ({score['grade']}등급)")
            if i <= 3:  # 하위 3개는 상세 정보 표시
                print(f"       CCTV: {score['cctv_count']}개, 성범죄자: {score['sexual_offender_count']}명")
    
    def _print_district_averages(self, safety_scores):
        """구별 평균 안전도 출력"""
        district_scores = defaultdict(list)
        for score in safety_scores:
            district_scores[score['district']].append(score['total_score'])
        
        district_avg = []
        for district, scores in district_scores.items():
            avg_score = sum(scores) / len(scores)
            district_avg.append((district, avg_score, len(scores)))
        
        district_avg.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n🏛️  구별 평균 안전도:")
        for i, (district, avg_score, dong_count) in enumerate(district_avg, 1):
            print(f"   {i:2d}. {district}: {avg_score:.1f}점 ({dong_count}개 동)")
    
    def _print_cpted_averages(self, safety_scores):
        """CPTED 원칙별 평균 점수 출력"""
        total_scores = len(safety_scores)
        avg_natural = sum(s['natural_surveillance'] for s in safety_scores) / total_scores
        avg_access = sum(s['access_control'] for s in safety_scores) / total_scores
        avg_territory = sum(s['territoriality'] for s in safety_scores) / total_scores
        avg_maintenance = sum(s['maintenance'] for s in safety_scores) / total_scores
        avg_activity = sum(s['activity_support'] for s in safety_scores) / total_scores
        
        print(f"\n🎯 CPTED 원칙별 서울시 평균 점수:")
        print(f"   자연적 감시 (CCTV, 가로등): {avg_natural:.1f}점")
        print(f"   접근통제 (성범죄자 정보): {avg_access:.1f}점")
        print(f"   영역성 강화 (경찰서, 안심시설): {avg_territory:.1f}점")
        print(f"   유지관리: {avg_maintenance:.1f}점")
        print(f"   활동성: {avg_activity:.1f}점")
    
    def export_to_csv(self, safety_scores, filename="safety_analysis_results.csv"):
        """분석 결과를 CSV 파일로 내보내기"""
        import csv
        
        if not safety_scores:
            print("❌ 내보낼 데이터가 없습니다.")
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'district', 'dong', 'total_score', 'grade',
                    'natural_surveillance', 'access_control', 'territoriality', 
                    'maintenance', 'activity_support',
                    'cctv_count', 'streetlight_count', 'police_station_count',
                    'female_safety_house_count', 'sexual_offender_count', 'delivery_box_count'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for score in safety_scores:
                    writer.writerow(score)
                
                print(f"✅ 분석 결과가 {filename}에 저장되었습니다.")
                
        except Exception as e:
            print(f"❌ CSV 파일 저장 중 오류 발생: {e}")
    
    def export_to_json(self, safety_scores, filename="safety_analysis_results.json"):
        """분석 결과를 JSON 파일로 내보내기"""
        import json
        
        if not safety_scores:
            print("❌ 내보낼 데이터가 없습니다.")
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(safety_scores, jsonfile, ensure_ascii=False, indent=2)
                
                print(f"✅ 분석 결과가 {filename}에 저장되었습니다.")
                
        except Exception as e:
            print(f"❌ JSON 파일 저장 중 오류 발생: {e}")
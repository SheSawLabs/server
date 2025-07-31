#!/usr/bin/env python3
"""
서울시 종합 안전도 분석 - 메인 실행 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.safety_analyzer import SafetyAnalyzer
from analysis.report_generator import SafetyReportGenerator
from analysis.detailed_report_generator import DetailedSafetyReportGenerator
import argparse

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='Seoul Safety Comprehensive Analysis')
    
    parser.add_argument(
        '--export-csv',
        action='store_true',
        help='Export results to CSV file'
    )
    
    parser.add_argument(
        '--export-json',
        action='store_true',
        help='Export results to JSON file'
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        help='Output filename (without extension)'
    )
    
    parser.add_argument(
        '--detailed-report',
        action='store_true',
        help='Generate detailed reports for top/bottom areas'
    )
    
    parser.add_argument(
        '--top-n',
        type=int,
        default=3,
        help='Number of top/bottom areas for detailed report (default: 3)'
    )
    
    args = parser.parse_args()
    
    print("🔒 서울시 종합 안전도 분석 시작")
    print("=" * 60)
    
    # 안전도 분석 실행
    analyzer = SafetyAnalyzer()
    safety_scores = analyzer.analyze_comprehensive_safety()
    
    if not safety_scores:
        print("❌ 분석 실패: 데이터가 없습니다.")
        return
    
    # 보고서 생성
    report_generator = SafetyReportGenerator()
    report_generator.generate_comprehensive_report(safety_scores)
    
    # 상세 리포트 생성
    if args.detailed_report:
        print(f"\n" + "="*100)
        print(f"📋 상세 분석 리포트 생성 중...")
        print(f"="*100)
        
        detailed_generator = DetailedSafetyReportGenerator()
        
        # 상위 N개 지역 상세 분석
        top_areas = sorted(safety_scores, key=lambda x: x['total_score'], reverse=True)[:args.top_n]
        for i, area in enumerate(top_areas, 1):
            print(f"\n🏆 상위 {i}위 지역 상세 분석:")
            detailed_generator.generate_dong_detailed_report(area)
        
        # 하위 N개 지역 상세 분석  
        bottom_areas = sorted(safety_scores, key=lambda x: x['total_score'])[:args.top_n]
        for i, area in enumerate(bottom_areas, 1):
            print(f"\n⚠️  하위 {i}위 지역 상세 분석:")
            detailed_generator.generate_dong_detailed_report(area)
    
    # 파일 내보내기
    base_filename = args.output_file or "seoul_safety_analysis"
    
    if args.export_csv:
        csv_filename = f"{base_filename}.csv"
        report_generator.export_to_csv(safety_scores, csv_filename)
    
    if args.export_json:
        json_filename = f"{base_filename}.json"
        report_generator.export_to_json(safety_scores, json_filename)
    
    print(f"\n✅ 분석 완료: 총 {len(safety_scores)}개 동 분석")
    
    return safety_scores

if __name__ == "__main__":
    results = main()
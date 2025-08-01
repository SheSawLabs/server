#!/usr/bin/env python3
"""
안전도 점수 재계산 스크립트 (등급 기준 조정 후)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from safety_score.dong_safety_calculator import DongSafetyCalculator

def main():
    """안전도 재계산 실행"""
    calculator = DongSafetyCalculator()
    
    print("🔄 안전도 등급 기준 조정 후 재계산 시작...")
    
    # 테스트로 50개 동 계산 (더 다양한 등급 분포 확인)
    results = calculator.calculate_all_dong_safety(limit=50)
    
    # 결과 출력
    print(f"\n🎯 재계산 완료!")
    print(f"   총 동 수: {results['total_dong']}개")
    print(f"   처리된 동: {results['processed']}개")
    print(f"   성공: {results['success']}개")
    print(f"   오류: {results['errors']}개")
    
    print(f"\n📊 새로운 등급별 분포:")
    for grade, count in results['grade_distribution'].items():
        percentage = (count / results['success'] * 100) if results['success'] > 0 else 0
        print(f"   {grade}등급: {count}개 ({percentage:.1f}%)")
    
    if results['top_scores']:
        print(f"\n🏆 안전도 상위 동:")
        for i, score in enumerate(results['top_scores'], 1):
            print(f"   {i}. {score['district']} {score['dong']}: {score['total_score']}점 ({score['safety_grade']}등급)")

if __name__ == "__main__":
    main()
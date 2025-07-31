#!/usr/bin/env python3
"""
성범죄자 공개 및 고지 지번 주소 정보 자동 수집 스케줄러

일정 간격으로 성범죄자 주소 데이터를 자동 수집하여 일일 API 제한 내에서 완료
일일 10,000회 제한에 맞춰 천천히 수집
"""

import schedule
import time
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers.sexual_offender_batch_controller import SexualOffenderBatchController

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SexualOffenderScheduler:
    """성범죄자 주소 데이터 자동 수집 스케줄러"""
    
    def __init__(self):
        self.controller = SexualOffenderBatchController()
        
        # 스케줄링 설정
        self.batch_size = 9000           # 한 번에 처리할 개수 (일일 제한 고려)
        self.interval_hours = 24         # 실행 간격 (24시간 = 하루에 한 번)
        self.daily_limit = 9500          # 일일 안전 한도
        self.daily_used = 0              # 오늘 사용한 API 호출 수
        self.last_reset_date = datetime.now().date()  # 마지막 리셋 날짜
        
        # 상태 추적
        self.is_running = False
        self.total_collected = 0
        self.start_time = None
    
    def reset_daily_counter(self):
        """날짜가 바뀌면 일일 카운터 리셋"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            logger.info(f"Daily counter reset: {self.daily_used} -> 0")
            self.daily_used = 0
            self.last_reset_date = current_date
    
    def check_daily_limit(self) -> bool:
        """일일 제한 확인"""
        self.reset_daily_counter()
        
        if self.daily_used >= self.daily_limit:
            logger.warning(f"Daily API limit reached: {self.daily_used}/{self.daily_limit}")
            return False
        
        remaining = self.daily_limit - self.daily_used
        if remaining < 1000:  # 최소 1000개는 처리해야 함
            logger.warning(f"Not enough API calls remaining: {remaining} < 1000")
            return False
        
        return True
    
    def get_progress_info(self) -> Dict[str, Any]:
        """현재 진행 상황 조회"""
        try:
            progress = self.controller.get_progress_info()
            return {
                'current_count': progress.get('current_count', 0),
                'total_count': progress.get('total_count', 0),
                'progress_percentage': progress.get('progress_percentage', 0),
                'remaining_count': progress.get('remaining_count', 0),
                'daily_api_used': self.daily_used,
                'daily_api_limit': self.daily_limit,
                'daily_api_remaining': self.daily_limit - self.daily_used
            }
        except Exception as e:
            logger.error(f"Error getting progress status: {e}")
            return {}
    
    def collect_batch(self):
        """배치 수집 실행"""
        logger.info("=" * 50)
        logger.info("Starting scheduled sexual offender data collection")
        
        try:
            # 일일 제한 확인
            if not self.check_daily_limit():
                logger.info("Skipping collection due to daily limit")
                return
            
            # 진행 상황 확인
            progress_before = self.get_progress_info()
            current_count = progress_before.get('current_count', 0)
            total_count = progress_before.get('total_count', 0)
            
            logger.info(f"Current progress: {current_count:,}/{total_count:,} ({progress_before.get('progress_percentage', 0):.1f}%)")
            
            # 완료 확인
            if current_count >= total_count:
                logger.info("🎉 All sexual offender data collection completed!")
                self.stop_scheduler()
                return
            
            # 배치 수집 실행
            logger.info(f"Collecting up to {self.batch_size} records...")
            start_time = time.time()
            
            # 다음 페이지 계산
            completed_pages = (current_count // 1000) + 1
            start_page = completed_pages if current_count % 1000 == 0 else completed_pages + 1
            
            logger.info(f"   Calculated start page: {start_page} (based on {current_count:,} existing records)")
            
            result = self.controller.run_batch_update(
                max_records=self.batch_size,
                start_page=start_page
            )
            
            execution_time = time.time() - start_time
            
            if result['success']:
                # 통계 업데이트
                api_calls_used = result.get('api_calls_used', 0)
                self.daily_used += api_calls_used
                self.total_collected += result.get('records_saved', 0)
                
                # 성공 로그
                logger.info(f"✅ Collection successful!")
                logger.info(f"   Records fetched: {result['records_fetched']:,}")
                logger.info(f"   Records saved: {result['records_saved']:,}")
                logger.info(f"   API calls used: {api_calls_used:,}")
                logger.info(f"   Execution time: {execution_time:.2f}s")
                logger.info(f"   Daily API usage: {self.daily_used:,}/{self.daily_limit:,}")
                
                # 업데이트 후 진행 상황
                progress_after = self.get_progress_info()
                logger.info(f"   Updated progress: {progress_after.get('current_count', 0):,}/{progress_after.get('total_count', 0):,} ({progress_after.get('progress_percentage', 0):.1f}%)")
                
                # 완료 예상 시간 계산
                remaining = progress_after.get('remaining_count', 0)
                if remaining > 0:
                    days_needed = remaining // self.batch_size + (1 if remaining % self.batch_size > 0 else 0)
                    eta = datetime.now() + timedelta(days=days_needed)
                    logger.info(f"   ETA: {eta.strftime('%Y-%m-%d')} (약 {days_needed}일 후)")
                
            else:
                logger.error(f"❌ Collection failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error in batch collection: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info("Scheduled collection completed")
        logger.info("=" * 50)
    
    def start_scheduler(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        
        logger.info("🚀 Starting sexual offender data collection scheduler")
        logger.info(f"   Batch size: {self.batch_size:,} records")
        logger.info(f"   Interval: {self.interval_hours} hours")
        logger.info(f"   Daily limit: {self.daily_limit:,} API calls")
        
        # 초기 상태 출력
        progress = self.get_progress_info()
        logger.info(f"   Current progress: {progress.get('current_count', 0):,}/{progress.get('total_count', 0):,}")
        
        # 스케줄 등록 (매일 실행)
        schedule.every(self.interval_hours).hours.do(self.collect_batch)
        
        # 즉시 한 번 실행
        logger.info("Running initial collection...")
        self.collect_batch()
        
        # 스케줄 실행 루프
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(3600)  # 1시간마다 스케줄 확인
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user")
        finally:
            self.stop_scheduler()
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        if not self.is_running:
            return
        
        self.is_running = False
        schedule.clear()
        
        runtime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        
        logger.info("⏹️ Sexual offender scheduler stopped")
        logger.info(f"   Total runtime: {runtime}")
        logger.info(f"   Total collected: {self.total_collected:,} records")
        logger.info(f"   API calls used today: {self.daily_used:,}/{self.daily_limit:,}")


def main():
    """메인 함수"""
    print("🏢 Seoul Sexual Offender Data Collection Scheduler 🏢")
    print()
    
    scheduler = SexualOffenderScheduler()
    
    try:
        # 현재 상태 확인
        progress = scheduler.get_progress_info()
        print(f"현재 진행 상황:")
        print(f"  저장된 데이터: {progress.get('current_count', 0):,}개")
        print(f"  전체 데이터: {progress.get('total_count', 0):,}개")
        print(f"  진행률: {progress.get('progress_percentage', 0):.1f}%")
        print(f"  오늘 API 사용: {progress.get('daily_api_used', 0):,}/{progress.get('daily_api_limit', 0):,}")
        print()
        
        if progress.get('remaining_count', 0) == 0:
            print("🎉 모든 데이터 수집이 완료되었습니다!")
            return
        
        # 예상 완료 시간
        remaining = progress.get('remaining_count', 0)
        days_needed = remaining // 9000 + (1 if remaining % 9000 > 0 else 0)
        print(f"📅 예상 완료: 약 {days_needed}일 후")
        print()
        
        # 사용자 확인
        response = input("자동 수집을 시작하시겠습니까? (y/N): ").lower().strip()
        if response != 'y':
            print("수집을 취소했습니다.")
            return
        
        # 스케줄러 시작
        scheduler.start_scheduler()
        
    except KeyboardInterrupt:
        print("\n사용자가 중단했습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
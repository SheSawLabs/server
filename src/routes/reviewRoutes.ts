import { Router } from 'express';
import { ReviewController } from '../controllers/reviewController';
import { optionalAuth } from '../middleware/auth';

const router = Router();
const reviewController = new ReviewController();

// GPT 키워드 추천
router.post('/recommend-keywords', (req, res) => {
  reviewController.getKeywordRecommendations(req, res);
});

// 점수 계산
router.post('/calculate-score', (req, res) => {
  reviewController.calculateScore(req, res);
});

// 키워드+별점 기반 분석 (줄글 선택적)
router.post('/analyze-keywords-rating', (req, res) => {
  reviewController.analyzeWithKeywordsAndRating(req, res);
});

// 통합 분석 (추천 + 점수계산)
router.post('/analyze-complete', optionalAuth, (req, res) => {
  reviewController.analyzeReviewComplete(req, res);
});

// 사용 가능한 키워드 목록
router.get('/keywords', (req, res) => {
  reviewController.getAvailableKeywords(req, res);
});

// =========================
// 리뷰 CRUD API
// =========================

// 리뷰 목록 조회 (무한 스크롤)
router.get('/list', optionalAuth, (req, res) => {
  reviewController.getReviews(req, res);
});

// 리뷰 상세 조회
router.get('/:id', (req, res) => {
  reviewController.getReview(req, res);
});

// 리뷰 수정
router.put('/:id', (req, res) => {
  reviewController.updateReview(req, res);
});

// 리뷰 삭제
router.delete('/:id', (req, res) => {
  reviewController.deleteReview(req, res);
});

// 전체 통계 정보 조회
router.get('/stats/summary', (req, res) => {
  reviewController.getReviewStats(req, res);
});

// 동별 통계 조회
router.get('/stats/location', (req, res) => {
  reviewController.getLocationStats(req, res);
});

export default router;
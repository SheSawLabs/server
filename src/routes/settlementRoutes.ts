import express from 'express';
import { authenticateToken } from '../middleware/auth';
import {
  createSettlementRequest,
  getSettlementRequest,
  getSettlementRequestsByPost,
  getMySettlementParticipations,
  updateSettlementRequestStatus,
  getSettlementStatistics
} from '../controllers/settlementController';

const router = express.Router();

// 정산 요청 생성 (인증 필요)
router.post('/', authenticateToken, createSettlementRequest);

// 정산 요청 상세 조회
router.get('/:settlementId', getSettlementRequest);

// 특정 게시물의 정산 요청 목록 조회
router.get('/post/:postId', getSettlementRequestsByPost);

// 사용자의 정산 참여 목록 조회 (인증 필요)
router.get('/my/participations', authenticateToken, getMySettlementParticipations);

// 정산 요청 상태 업데이트 (인증 필요)
router.patch('/:settlementId/status', authenticateToken, updateSettlementRequestStatus);

// 정산 통계 조회 (인증 필요)
router.get('/:settlementId/statistics', authenticateToken, getSettlementStatistics);

export default router;
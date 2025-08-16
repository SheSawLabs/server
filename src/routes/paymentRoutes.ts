import express from 'express';
import { authenticateToken } from '../middleware/auth';
import {
  startSettlementPayment,
  confirmSettlementPayment,
  handleSettlementPaymentFailure,
  getPaymentInfo,
  cancelPayment,
  getSettlementPaymentStatus
} from '../controllers/paymentController';

const router = express.Router();

// 정산 결제 시작 (인증 필요)
router.post('/settlement/start', authenticateToken, startSettlementPayment);

// 정산 결제 승인 (인증 필요)
router.post('/settlement/confirm', authenticateToken, confirmSettlementPayment);

// 정산 결제 실패 처리 (인증 필요)
router.post('/settlement/fail', authenticateToken, handleSettlementPaymentFailure);

// 정산 결제 상태 조회 (인증 필요)
router.get('/settlement/status', authenticateToken, getSettlementPaymentStatus);

// 결제 정보 조회
router.get('/:paymentKey', getPaymentInfo);

// 결제 취소 (인증 필요)
router.post('/:paymentKey/cancel', authenticateToken, cancelPayment);

export default router;
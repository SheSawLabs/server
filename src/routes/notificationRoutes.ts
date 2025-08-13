import { Router } from 'express';
import { NotificationController } from '../controllers/notificationController';
import { authenticateToken } from '../middleware/auth';

const router = Router();

/**
 * 커뮤니티 알림 키워드 추가
 * POST /api/notifications/keywords
 * Authorization: Bearer {token}
 * Body: { keyword: string }
 */
router.post('/keywords', authenticateToken, NotificationController.createKeyword);

/**
 * 사용자별 알림 키워드 목록 조회
 * GET /api/notifications/keywords
 * Authorization: Bearer {token}
 */
router.get('/keywords', authenticateToken, NotificationController.getKeywords);

/**
 * 알림 키워드 삭제
 * DELETE /api/notifications/keywords/:keyword
 * Authorization: Bearer {token}
 */
router.delete('/keywords/:keyword', authenticateToken, NotificationController.deleteKeyword);

export default router;
import { Router } from 'express';
import { AuthController } from '../controllers/authController';
import { authenticateToken } from '../middleware/auth';

const router = Router();

/**
 * 카카오 로그인 시작 - 카카오 로그인 페이지로 리다이렉트
 * GET /auth/kakao
 */
router.get('/kakao', AuthController.redirectToKakao);

/**
 * 카카오 OAuth 콜백 처리 - 인증 코드를 받아 토큰 생성
 * GET /auth/kakao/callback
 */
router.get('/kakao/callback', AuthController.handleKakaoCallback);

/**
 * 토큰 검증 및 사용자 정보 조회
 * GET /auth/verify
 * Authorization: Bearer {token}
 */
router.get('/verify', AuthController.verifyToken);

/**
 * 로그아웃 처리
 * POST /auth/logout
 * Authorization: Bearer {token}
 */
router.post('/logout', authenticateToken, AuthController.logout);

/**
 * 보호된 라우트 예시 - 인증된 사용자만 접근 가능
 * GET /auth/profile
 * Authorization: Bearer {token}
 */
router.get('/profile', authenticateToken, (req, res) => {
  res.json({
    success: true,
    message: '사용자 프로필 정보입니다.',
    data: {
      user: req.user
    }
  });
});

export default router;
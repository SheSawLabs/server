import express from 'express';
import { generateTestToken, generateMultipleTestTokens } from '../controllers/testController';

const router = express.Router();

// 개별 테스트 토큰 생성
router.post('/token', generateTestToken);

// 여러 테스트 토큰 한 번에 생성  
router.post('/tokens', generateMultipleTestTokens);

export default router;
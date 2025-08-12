import express from 'express';
import { getPolicies, getPolicyById, deleteAllPolicies } from '../controllers/policyController';

const router = express.Router();

// 모든 정책 조회 (카테고리 필터링 옵션)
router.get('/', getPolicies);                    // GET /api/policies?category=여성

// 내부용: 모든 정책 삭제 (특정 라우트보다 먼저 배치)
router.delete('/internal/delete-all', deleteAllPolicies);  // DELETE /api/policies/internal/delete-all

// 특정 정책 조회
router.get('/:id', getPolicyById);               // GET /api/policies/:id

export default router;
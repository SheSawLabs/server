import express from 'express';
import { RestrictedReviewController } from '../controllers/restrictedReviewController';

const router = express.Router();
const controller = new RestrictedReviewController();

/**
 * @swagger
 * /api/restricted/analyze-restricted:
 *   post:
 *     tags: [제한적 분석 (무료)]
 *     summary: 제한적 AI 분석
 *     description: |
 *       사전 정의된 CPTED 키워드만 사용하여 리뷰를 분석합니다.
 *       OpenAI API를 사용하지 않으므로 완전 무료입니다.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/ReviewAnalysisRequest'
 *           example:
 *             reviewText: "밤에 이 길을 걸으면 가로등이 부족해서 너무 어둡고 무서워요."
 *             location: "강남구 역삼동"
 *             timeOfDay: "밤"
 *             rating: 2
 *     responses:
 *       200:
 *         description: 분석 성공
 *         content:
 *           application/json:
 *             schema:
 *               allOf:
 *                 - $ref: '#/components/schemas/ApiResponse'
 *                 - type: object
 *                   properties:
 *                     method:
 *                       type: string
 *                       example: "restricted"
 *                     data:
 *                       type: object
 *                       properties:
 *                         recommendedKeywords:
 *                           type: array
 *                           items:
 *                             $ref: '#/components/schemas/KeywordRecommendation'
 *                         scoreResult:
 *                           $ref: '#/components/schemas/ScoreResult'
 *                         contextAnalysis:
 *                           type: object
 *                           description: 맥락 분석 결과
 *       400:
 *         description: 잘못된 요청
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ApiResponse'
 *             example:
 *               success: false
 *               error: "리뷰 텍스트가 필요합니다."
 */
router.post('/analyze-restricted', controller.analyzeReviewRestricted.bind(controller));

/**
 * @swagger
 * /api/restricted/analyze-keywords:
 *   post:
 *     tags: [제한적 분석 (무료)]
 *     summary: 키워드 기반 분석
 *     description: 미리 선택된 키워드만으로 분석합니다 (텍스트 없이).
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               selectedKeywords:
 *                 type: array
 *                 items:
 *                   $ref: '#/components/schemas/SelectedKeyword'
 *                 example:
 *                   - category: "naturalSurveillance"
 *                     keyword: "어두움"
 *                   - category: "emotional"
 *                     keyword: "불안"
 *               location:
 *                 type: string
 *                 example: "강남구 역삼동"
 *               timeOfDay:
 *                 type: string
 *                 example: "밤"
 *               rating:
 *                 type: integer
 *                 example: 2
 *             required: [selectedKeywords]
 *     responses:
 *       200:
 *         description: 분석 성공
 *       400:
 *         description: 잘못된 요청
 */
router.post('/analyze-keywords', controller.analyzeByKeywordsOnly.bind(controller));

/**
 * @swagger
 * /api/restricted/recommend-keywords:
 *   post:
 *     tags: [제한적 분석 (무료)]
 *     summary: 키워드 추천만
 *     description: 텍스트에서 키워드만 추천합니다 (GPT 없이).
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               reviewText:
 *                 type: string
 *                 example: "공원 근처라서 사람들이 많이 다니고 밝아서 안전해 보여요."
 *               location:
 *                 type: string
 *                 example: "강남구 역삼동"
 *               timeOfDay:
 *                 type: string
 *                 example: "오후"
 *             required: [reviewText]
 *     responses:
 *       200:
 *         description: 키워드 추천 성공
 *       400:
 *         description: 잘못된 요청
 */
router.post('/recommend-keywords', controller.getKeywordRecommendationsOnly.bind(controller));

/**
 * @swagger
 * /api/restricted/system-info:
 *   get:
 *     tags: [시스템 정보]
 *     summary: 시스템 정보 조회
 *     description: 사용 가능한 키워드 목록과 시스템 정보를 반환합니다.
 *     responses:
 *       200:
 *         description: 시스템 정보 조회 성공
 *         content:
 *           application/json:
 *             schema:
 *               allOf:
 *                 - $ref: '#/components/schemas/ApiResponse'
 *                 - type: object
 *                   properties:
 *                     data:
 *                       type: object
 *                       properties:
 *                         system:
 *                           type: object
 *                           properties:
 *                             analysisMethod:
 *                               type: string
 *                               example: "restricted"
 *                             description:
 *                               type: string
 *                               example: "사전 정의된 CPTED 키워드만 사용하는 제한적 분석 시스템"
 *                             features:
 *                               type: array
 *                               items:
 *                                 type: string
 *                               example: ["공공데이터 기반 분석", "사전 정의된 키워드만 사용"]
 *                         availableKeywords:
 *                           type: object
 *                           additionalProperties:
 *                             type: array
 *                             items:
 *                               type: string
 *                           example:
 *                             "자연적 감시": ["밝음", "어두움", "시야트임"]
 *                             "감정형": ["안심", "약간불안", "불안", "위험"]
 *                         totalKeywords:
 *                           type: integer
 *                           example: 20
 *                         categories:
 *                           type: integer
 *                           example: 6
 */
router.get('/system-info', controller.getSystemInfo.bind(controller));

export default router;
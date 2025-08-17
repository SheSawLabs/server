import { Request, Response } from 'express';
import { JWTUtil } from '../utils/jwt';
import { pool } from '../config/database';

/**
 * 테스트용 JWT 토큰 생성
 * 개발/테스트 환경에서만 사용, 운영환경에서는 제거 필요
 */
export const generateTestToken = async (req: Request, res: Response) => {
  try {
    // 운영환경에서는 비활성화
    if (process.env.NODE_ENV === 'production') {
      return res.status(403).json({
        success: false,
        message: '운영환경에서는 사용할 수 없습니다.'
      });
    }

    const { user_id, nickname = `테스트사용자${user_id}`, email } = req.body;

    // user_id 검증 (10 이상만 허용)
    if (!user_id || parseInt(user_id) < 10) {
      return res.status(400).json({
        success: false,
        message: 'user_id는 10 이상이어야 합니다.'
      });
    }

    // 토큰 생성에 필요한 payload (iat, exp 제외)
    const tokenPayload = {
      user_id: user_id.toString(),
      email: email || `test${user_id}@example.com`,
      nickname: nickname,
      provider: 'test',
      providerId: `test_${user_id}`
    };

    // JWT 토큰 생성
    const token = JWTUtil.generateToken(tokenPayload);

    res.json({
      success: true,
      message: '테스트용 토큰이 생성되었습니다.',
      data: {
        token,
        user: {
          user_id: tokenPayload.user_id,
          email: tokenPayload.email,
          nickname: tokenPayload.nickname
        },
        expires_in: '24h'
      }
    });

  } catch (error) {
    console.error('테스트 토큰 생성 오류:', error);
    res.status(500).json({
      success: false,
      message: '토큰 생성에 실패했습니다.'
    });
  }
};

/**
 * 여러 사용자의 테스트 토큰을 한 번에 생성
 */
export const generateMultipleTestTokens = async (req: Request, res: Response) => {
  try {
    // 운영환경에서는 비활성화
    if (process.env.NODE_ENV === 'production') {
      return res.status(403).json({
        success: false,
        message: '운영환경에서는 사용할 수 없습니다.'
      });
    }

    const { count = 5, start_id = 10 } = req.body;

    if (count > 20) {
      return res.status(400).json({
        success: false,
        message: '최대 20개까지 생성 가능합니다.'
      });
    }

    if (start_id < 10) {
      return res.status(400).json({
        success: false,
        message: '시작 user_id는 10 이상이어야 합니다.'
      });
    }

    // 랜덤 닉네임 생성용 배열들
    const dongNames = [
      '자곡동', '역삼동', '강남동', '서초동', '압구정동', '청담동', '논현동', '신사동',
      '한남동', '이태원동', '명동', '종로동', '중구동', '마포동', '홍대동', '합정동',
      '연남동', '상수동', '망원동', '성수동', '건대동', '왕십리동', '성북동', '혜화동'
    ];
    
    const foodNames = [
      '불막창', '김치찌개', '삼겹살', '치킨', '피자', '햄버거', '떡볶이', '순대',
      '라면', '냉면', '갈비탕', '설렁탕', '삼계탕', '비빔밥', '김밥', '토스트',
      '파스타', '스테이크', '초밥', '우동', '돈까스', '짜장면', '탕수육', '마라탕'
    ];

    const getRandomNickname = () => {
      const dong = dongNames[Math.floor(Math.random() * dongNames.length)];
      const food = foodNames[Math.floor(Math.random() * foodNames.length)];
      return `${dong} ${food}`;
    };

    const tokens = [];

    for (let i = 0; i < count; i++) {
      const user_id = start_id + i;
      const nickname = getRandomNickname();
      const email = `test${user_id}@example.com`;
      
      // DB에 사용자 저장 (이미 존재하면 업데이트)
      await pool.query(`
        INSERT INTO users (id, provider, provider_id, email, nickname, profile_image)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (provider, provider_id) 
        DO UPDATE SET 
          email = EXCLUDED.email,
          updated_at = NOW()
      `, [user_id, 'test', `test_${user_id}`, email, nickname, null]);

      const tokenPayload = {
        user_id: user_id.toString(),
        email: email,
        nickname: nickname,
        provider: 'test',
        providerId: `test_${user_id}`
      };

      const token = JWTUtil.generateToken(tokenPayload);
      
      tokens.push({
        user_id: user_id,
        nickname: nickname,
        email: email,
        token: token
      });
    }

    res.json({
      success: true,
      message: `${count}개의 테스트 토큰이 생성되었습니다.`,
      data: tokens
    });

  } catch (error) {
    console.error('다중 테스트 토큰 생성 오류:', error);
    res.status(500).json({
      success: false,
      message: '토큰 생성에 실패했습니다.'
    });
  }
};
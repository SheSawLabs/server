import { Request, Response, NextFunction } from 'express';
import { JWTUtil } from '../utils/jwt';
import { AuthTokenPayload } from '../types';

// Request 타입 확장
declare global {
  namespace Express {
    interface Request {
      user?: AuthTokenPayload;
    }
  }
}

/**
 * JWT 토큰 검증 미들웨어
 */
export const authenticateToken = (req: Request, res: Response, next: NextFunction): void => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).json({
        success: false,
        message: '인증 토큰이 제공되지 않았습니다.',
        error: 'Missing authorization token'
      });
      return;
    }

    const token = authHeader.substring(7); // 'Bearer ' 제거
    const decoded = JWTUtil.verifyToken(token);
    
    req.user = decoded;
    next();
    
  } catch (error) {
    console.error('토큰 검증 실패:', error);
    res.status(401).json({
      success: false,
      message: '유효하지 않은 토큰입니다.',
      error: error instanceof Error ? error.message : '알 수 없는 오류'
    });
  }
};

/**
 * 선택적 인증 미들웨어 (토큰이 있으면 검증, 없어도 통과)
 */
export const optionalAuth = (req: Request, res: Response, next: NextFunction): void => {
  try {
    const authHeader = req.headers.authorization;
    
    if (authHeader && authHeader.startsWith('Bearer ')) {
      const token = authHeader.substring(7);
      const decoded = JWTUtil.verifyToken(token);
      req.user = decoded;
    }
    
    next();
    
  } catch (error) {
    // 선택적 인증이므로 오류가 있어도 계속 진행
    console.warn('선택적 토큰 검증 실패:', error);
    next();
  }
};
import jwt, { SignOptions } from 'jsonwebtoken';
import { config } from '../config';
import { AuthTokenPayload } from '../types';

export class JWTUtil {
  /**
   * JWT 토큰 생성
   */
  static generateToken(payload: Omit<AuthTokenPayload, 'iat' | 'exp'>): string {
    if (!config.jwt.secret) {
      throw new Error('JWT secret is not configured');
    }
    return jwt.sign(payload, config.jwt.secret, {
      expiresIn: config.jwt.expiresIn as any
    });
  }
  
  /**
   * JWT 토큰 검증
   */
  static verifyToken(token: string): AuthTokenPayload {
    try {
      if (!config.jwt.secret) {
        throw new Error('JWT secret is not configured');
      }
      return jwt.verify(token, config.jwt.secret) as AuthTokenPayload;
    } catch (error) {
      throw new Error('유효하지 않은 토큰입니다.');
    }
  }
  
  /**
   * JWT 토큰 디코딩 (검증 없이)
   */
  static decodeToken(token: string): AuthTokenPayload | null {
    try {
      return jwt.decode(token) as AuthTokenPayload;
    } catch (error) {
      return null;
    }
  }
}
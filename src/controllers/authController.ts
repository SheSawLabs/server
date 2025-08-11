import { Request, Response } from 'express';
import { KakaoOAuth } from '../utils/kakao';
import { JWTUtil } from '../utils/jwt';
import { UserModel } from '../models/User';
import { AuthResponse } from '../types';

export class AuthController {
  /**
   * 카카오 로그인 페이지 리다이렉트
   */
  static async redirectToKakao(req: Request, res: Response): Promise<void> {
    try {
      const authUrl = KakaoOAuth.getAuthUrl();
      res.redirect(authUrl);
    } catch (error) {
      console.error('카카오 로그인 리다이렉트 실패:', error);
      res.status(500).json({
        success: false,
        message: '카카오 로그인 페이지로 이동할 수 없습니다.',
        error: error instanceof Error ? error.message : '알 수 없는 오류'
      } as AuthResponse);
    }
  }

  /**
   * 카카오 OAuth 콜백 처리
   */
  static async handleKakaoCallback(req: Request, res: Response): Promise<void> {
    try {
      const { code } = req.query;

      if (!code || typeof code !== 'string') {
        res.status(400).json({
          success: false,
          message: '인증 코드가 제공되지 않았습니다.',
          error: 'Missing authorization code'
        } as AuthResponse);
        return;
      }

      // 1. 액세스 토큰 획득
      const accessToken = await KakaoOAuth.getAccessToken(code);

      // 2. 사용자 정보 획득
      const kakaoUserInfo = await KakaoOAuth.getUserInfo(accessToken);

      // 3. DB에 사용자 저장 또는 업데이트
      const user = await UserModel.findOrCreateKakaoUser(kakaoUserInfo);

      // 4. JWT 토큰 생성
      const jwtToken = JWTUtil.generateToken({
        user_id: user.id,
        provider: user.provider,
        providerId: user.providerId,
        email: user.email,
        nickname: user.nickname
      });

      // 5. 성공 응답
      res.json({
        success: true,
        message: '로그인이 완료되었습니다.',
        data: {
          token: jwtToken,
          user: user
        }
      } as AuthResponse);

    } catch (error) {
      console.error('카카오 콜백 처리 실패:', error);
      res.status(500).json({
        success: false,
        message: '로그인 처리 중 오류가 발생했습니다.',
        error: error instanceof Error ? error.message : '알 수 없는 오류'
      } as AuthResponse);
    }
  }

  /**
   * 토큰 검증 및 사용자 정보 반환
   */
  static async verifyToken(req: Request, res: Response): Promise<void> {
    try {
      const authHeader = req.headers.authorization;
      
      if (!authHeader || !authHeader.startsWith('Bearer ')) {
        res.status(401).json({
          success: false,
          message: '토큰이 제공되지 않았습니다.',
          error: 'Missing authorization token'
        } as AuthResponse);
        return;
      }

      const token = authHeader.substring(7); // 'Bearer ' 제거
      const decoded = JWTUtil.verifyToken(token);

      res.json({
        success: true,
        message: '토큰이 유효합니다.',
        data: {
          token: token,
          user: await UserModel.findById(parseInt(decoded.user_id)) || {
            id: decoded.user_id,
            provider: decoded.provider,
            providerId: decoded.providerId,
            kakao_id: decoded.providerId || '',
            email: decoded.email,
            nickname: decoded.nickname || '',
            created_at: new Date(),
            updated_at: new Date(),
            profileImage: null,
            thumbnailImage: null,
            gender: null,
            birthday: null,
            birthyear: null,
            ageRange: null,
            mobile: null,
            createdAt: new Date(),
            updatedAt: new Date(),
            lastLoginAt: new Date()
          }
        }
      } as AuthResponse);

    } catch (error) {
      console.error('토큰 검증 실패:', error);
      res.status(401).json({
        success: false,
        message: '유효하지 않은 토큰입니다.',
        error: error instanceof Error ? error.message : '알 수 없는 오류'
      } as AuthResponse);
    }
  }

  /**
   * 로그아웃 처리
   */
  static async logout(req: Request, res: Response): Promise<void> {
    try {
      // 클라이언트 측에서 토큰 삭제하도록 안내
      res.json({
        success: true,
        message: '로그아웃이 완료되었습니다. 클라이언트에서 토큰을 삭제해주세요.'
      } as AuthResponse);
    } catch (error) {
      console.error('로그아웃 처리 실패:', error);
      res.status(500).json({
        success: false,
        message: '로그아웃 처리 중 오류가 발생했습니다.',
        error: error instanceof Error ? error.message : '알 수 없는 오류'
      } as AuthResponse);
    }
  }
}
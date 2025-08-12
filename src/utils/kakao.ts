import axios from 'axios';
import { config } from '../config';
import { KakaoUserInfo, KakaoTokenResponse } from '../types';

export class KakaoOAuth {
  /**
   * 카카오 OAuth 인증 URL 생성
   */
  static getAuthUrl(): string {
    const params = new URLSearchParams({
      client_id: config.kakao.clientId,
      redirect_uri: config.kakao.redirectUri,
      response_type: 'code',
      scope: 'profile_nickname,profile_image'
    });
    
    return `https://kauth.kakao.com/oauth/authorize?${params.toString()}`;
  }
  
  /**
   * 인증 코드로 액세스 토큰 획득
   */
  static async getAccessToken(code: string): Promise<string> {
    try {
      const response = await axios.post<KakaoTokenResponse>(
        'https://kauth.kakao.com/oauth/token',
        {
          grant_type: 'authorization_code',
          client_id: config.kakao.clientId,
          client_secret: config.kakao.clientSecret,
          redirect_uri: config.kakao.redirectUri,
          code: code
        },
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        }
      );
      
      return response.data.access_token;
    } catch (error: any) {
      console.error('액세스 토큰 획득 실패:', error.response?.data || error.message);
      throw new Error('액세스 토큰 획득에 실패했습니다.');
    }
  }
  
  /**
   * 액세스 토큰으로 사용자 정보 획득
   */
  static async getUserInfo(accessToken: string): Promise<KakaoUserInfo> {
    try {
      const response = await axios.get('https://kapi.kakao.com/v2/user/me', {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      const { id, kakao_account } = response.data;
      
      return {
        id: parseInt(id),
        connected_at: new Date().toISOString(),
        properties: {
          nickname: kakao_account.profile?.nickname || '',
          profile_image: kakao_account.profile?.profile_image_url,
          thumbnail_image: kakao_account.profile?.thumbnail_image_url
        },
        kakao_account: {
          profile_nickname_needs_agreement: false,
          profile_image_needs_agreement: false,
          profile: {
            nickname: kakao_account.profile?.nickname || '',
            thumbnail_image_url: kakao_account.profile?.thumbnail_image_url,
            profile_image_url: kakao_account.profile?.profile_image_url,
            is_default_image: false
          },
          has_email: !!kakao_account.email,
          email_needs_agreement: false,
          is_email_valid: true,
          is_email_verified: true,
          email: kakao_account.email || ''
        },
        // Additional properties for easier access
        email: kakao_account.email,
        nickname: kakao_account.profile?.nickname,
        profileImage: kakao_account.profile?.profile_image_url,
        thumbnailImage: kakao_account.profile?.thumbnail_image_url
      };
    } catch (error: any) {
      console.error('사용자 정보 획득 실패:', error.response?.data || error.message);
      throw new Error('사용자 정보 획득에 실패했습니다.');
    }
  }
}
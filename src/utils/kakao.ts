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
    
    return `${config.kakao.authUrl}?${params.toString()}`;
  }
  
  /**
   * 인증 코드로 액세스 토큰 획득
   */
  static async getAccessToken(code: string): Promise<string> {
    try {
      const response = await axios.post<KakaoTokenResponse>(
        config.kakao.tokenUrl,
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
      const response = await axios.get(config.kakao.userInfoUrl, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      const { id, kakao_account } = response.data;
      
      return {
        id: id.toString(),
        email: kakao_account.email || null,
        nickname: kakao_account.profile?.nickname || null,
        profileImage: kakao_account.profile?.profile_image_url || null,
        thumbnailImage: kakao_account.profile?.thumbnail_image_url || null
      };
    } catch (error: any) {
      console.error('사용자 정보 획득 실패:', error.response?.data || error.message);
      throw new Error('사용자 정보 획득에 실패했습니다.');
    }
  }
}
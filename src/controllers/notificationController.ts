import { Request, Response } from 'express';
import { NotificationKeywordModel } from '../models/notificationKeyword';

export class NotificationController {
  // 키워드 추가
  static async createKeyword(req: Request, res: Response): Promise<void> {
    try {
      const { keyword } = req.body;
      const userId = req.user?.user_id ? parseInt(req.user.user_id) : undefined;

      if (!keyword || !keyword.trim()) {
        res.status(400).json({
          success: false,
          message: '키워드는 필수입니다.'
        });
        return;
      }

      if (!userId) {
        res.status(401).json({
          success: false,
          message: '인증이 필요합니다.'
        });
        return;
      }

      // 키워드 중복 확인
      const exists = await NotificationKeywordModel.checkKeywordExists(userId, keyword.trim());
      if (exists) {
        res.status(400).json({
          success: false,
          message: '이미 등록된 키워드입니다.'
        });
        return;
      }

      const newKeyword = await NotificationKeywordModel.createKeyword(userId, keyword.trim());

      res.status(201).json({
        success: true,
        message: '키워드가 성공적으로 등록되었습니다.',
        data: newKeyword
      });
    } catch (error) {
      console.error('키워드 생성 오류:', error);
      res.status(500).json({
        success: false,
        message: '서버 오류가 발생했습니다.'
      });
    }
  }

  // 사용자 키워드 목록 조회
  static async getKeywords(req: Request, res: Response): Promise<void> {
    try {
      const userId = req.user?.user_id ? parseInt(req.user.user_id) : undefined;

      if (!userId) {
        res.status(401).json({
          success: false,
          message: '인증이 필요합니다.'
        });
        return;
      }

      const keywords = await NotificationKeywordModel.getKeywordsByUserId(userId);

      res.json({
        success: true,
        data: keywords
      });
    } catch (error) {
      console.error('키워드 조회 오류:', error);
      res.status(500).json({
        success: false,
        message: '서버 오류가 발생했습니다.'
      });
    }
  }

  // 키워드 삭제
  static async deleteKeyword(req: Request, res: Response): Promise<void> {
    try {
      const { keyword } = req.params;
      const userId = req.user?.user_id ? parseInt(req.user.user_id) : undefined;

      if (!keyword) {
        res.status(400).json({
          success: false,
          message: '키워드는 필수입니다.'
        });
        return;
      }

      if (!userId) {
        res.status(401).json({
          success: false,
          message: '인증이 필요합니다.'
        });
        return;
      }

      const deleted = await NotificationKeywordModel.deleteKeyword(userId, decodeURIComponent(keyword));

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: '키워드를 찾을 수 없습니다.'
        });
        return;
      }

      res.json({
        success: true,
        message: '키워드가 성공적으로 삭제되었습니다.'
      });
    } catch (error) {
      console.error('키워드 삭제 오류:', error);
      res.status(500).json({
        success: false,
        message: '서버 오류가 발생했습니다.'
      });
    }
  }
}
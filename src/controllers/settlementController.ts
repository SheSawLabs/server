import { Request, Response } from 'express';
import { SettlementModel, CreateSettlementRequest } from '../models/settlement';

export interface AuthenticatedRequest extends Request {
  user?: {
    user_id: string;
    email: string;
    nickname?: string;
    provider?: string;
    providerId?: string;
    iat: number;
    exp: number;
  };
}

/**
 * 정산 요청 생성
 */
export const createSettlementRequest = async (req: AuthenticatedRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ 
        success: false, 
        message: '인증이 필요합니다.' 
      });
    }

    const { post_id, total_amount, participants } = req.body;

    // 필수 필드 검증
    if (!post_id || !total_amount || !participants || !Array.isArray(participants)) {
      return res.status(400).json({
        success: false,
        message: '필수 필드가 누락되었습니다. (post_id, total_amount, participants)'
      });
    }

    // 총 금액 검증
    if (total_amount <= 0) {
      return res.status(400).json({
        success: false,
        message: '총 금액은 0보다 커야 합니다.'
      });
    }

    // 참여자 데이터 검증
    if (participants.length === 0) {
      return res.status(400).json({
        success: false,
        message: '최소 1명 이상의 참여자가 필요합니다.'
      });
    }

    for (const participant of participants) {
      if (!participant.user_id || !participant.amount || participant.amount <= 0) {
        return res.status(400).json({
          success: false,
          message: '모든 참여자는 유효한 user_id와 양수인 amount를 가져야 합니다.'
        });
      }
    }

    // 참여자 금액 합계 검증
    const participantsTotal = participants.reduce((sum: number, p: any) => sum + p.amount, 0);
    if (participantsTotal !== total_amount) {
      return res.status(400).json({
        success: false,
        message: '참여자들의 금액 합계가 총 금액과 일치하지 않습니다.'
      });
    }

    const settlementData: CreateSettlementRequest = {
      post_id,
      creator_id: parseInt(req.user.user_id),
      total_amount,
      participants
    };

    const settlement = await SettlementModel.createSettlementRequest(settlementData);

    res.status(201).json({
      success: true,
      message: '정산 요청이 성공적으로 생성되었습니다.',
      data: settlement
    });
  } catch (error) {
    console.error('정산 요청 생성 오류:', error);
    res.status(500).json({
      success: false,
      message: '정산 요청 생성에 실패했습니다.'
    });
  }
};

/**
 * 정산 요청 상세 조회
 */
export const getSettlementRequest = async (req: Request, res: Response) => {
  try {
    const { settlementId } = req.params;

    if (!settlementId) {
      return res.status(400).json({
        success: false,
        message: '정산 요청 ID가 필요합니다.'
      });
    }

    const settlement = await SettlementModel.getSettlementRequestWithParticipants(settlementId);

    if (!settlement) {
      return res.status(404).json({
        success: false,
        message: '정산 요청을 찾을 수 없습니다.'
      });
    }

    res.json({
      success: true,
      data: settlement
    });
  } catch (error) {
    console.error('정산 요청 조회 오류:', error);
    res.status(500).json({
      success: false,
      message: '정산 요청 조회에 실패했습니다.'
    });
  }
};

/**
 * 특정 게시물의 정산 요청 목록 조회
 */
export const getSettlementRequestsByPost = async (req: Request, res: Response) => {
  try {
    const { postId } = req.params;

    if (!postId) {
      return res.status(400).json({
        success: false,
        message: '게시물 ID가 필요합니다.'
      });
    }

    const settlements = await SettlementModel.getSettlementRequestsByPostId(postId);

    res.json({
      success: true,
      data: settlements
    });
  } catch (error) {
    console.error('게시물 정산 요청 목록 조회 오류:', error);
    res.status(500).json({
      success: false,
      message: '정산 요청 목록 조회에 실패했습니다.'
    });
  }
};

/**
 * 사용자의 정산 참여 목록 조회 (결제해야 할 목록)
 */
export const getMySettlementParticipations = async (req: AuthenticatedRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: '인증이 필요합니다.'
      });
    }

    const settlements = await SettlementModel.getSettlementParticipationsByUserId(parseInt(req.user.user_id));

    res.json({
      success: true,
      data: settlements
    });
  } catch (error) {
    console.error('정산 참여 목록 조회 오류:', error);
    res.status(500).json({
      success: false,
      message: '정산 참여 목록 조회에 실패했습니다.'
    });
  }
};

/**
 * 정산 요청 상태 업데이트 (작성자만 가능)
 */
export const updateSettlementRequestStatus = async (req: AuthenticatedRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: '인증이 필요합니다.'
      });
    }

    const { settlementId } = req.params;
    const { status } = req.body;

    if (!settlementId || !status) {
      return res.status(400).json({
        success: false,
        message: '정산 요청 ID와 상태가 필요합니다.'
      });
    }

    const validStatuses = ['pending', 'in_progress', 'completed', 'cancelled'];
    if (!validStatuses.includes(status)) {
      return res.status(400).json({
        success: false,
        message: `유효하지 않은 상태입니다. 허용된 값: ${validStatuses.join(', ')}`
      });
    }

    // 정산 요청 조회 및 권한 확인
    const existingSettlement = await SettlementModel.getSettlementRequestWithParticipants(settlementId);
    if (!existingSettlement) {
      return res.status(404).json({
        success: false,
        message: '정산 요청을 찾을 수 없습니다.'
      });
    }

    if (existingSettlement.creator_id !== parseInt(req.user.user_id)) {
      return res.status(403).json({
        success: false,
        message: '정산 요청 작성자만 상태를 변경할 수 있습니다.'
      });
    }

    const updatedSettlement = await SettlementModel.updateSettlementRequestStatus(settlementId, status);

    res.json({
      success: true,
      message: '정산 요청 상태가 성공적으로 업데이트되었습니다.',
      data: updatedSettlement
    });
  } catch (error) {
    console.error('정산 요청 상태 업데이트 오류:', error);
    res.status(500).json({
      success: false,
      message: '정산 요청 상태 업데이트에 실패했습니다.'
    });
  }
};

/**
 * 정산 통계 조회 (작성자용)
 */
export const getSettlementStatistics = async (req: AuthenticatedRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: '인증이 필요합니다.'
      });
    }

    const { settlementId } = req.params;

    const settlement = await SettlementModel.getSettlementRequestWithParticipants(settlementId);
    if (!settlement) {
      return res.status(404).json({
        success: false,
        message: '정산 요청을 찾을 수 없습니다.'
      });
    }

    if (settlement.creator_id !== parseInt(req.user.user_id)) {
      return res.status(403).json({
        success: false,
        message: '정산 요청 작성자만 통계를 조회할 수 있습니다.'
      });
    }

    // 결제 상태별 통계 계산
    const statistics = {
      total_participants: settlement.participants.length,
      total_amount: settlement.total_amount,
      paid_count: settlement.participants.filter(p => p.payment_status === 'paid').length,
      pending_count: settlement.participants.filter(p => p.payment_status === 'pending').length,
      failed_count: settlement.participants.filter(p => p.payment_status === 'failed').length,
      refunded_count: settlement.participants.filter(p => p.payment_status === 'refunded').length,
      paid_amount: settlement.participants
        .filter(p => p.payment_status === 'paid')
        .reduce((sum, p) => sum + p.amount, 0),
      pending_amount: settlement.participants
        .filter(p => p.payment_status === 'pending')
        .reduce((sum, p) => sum + p.amount, 0),
      completion_rate: settlement.participants.length > 0 
        ? Math.round((settlement.participants.filter(p => p.payment_status === 'paid').length / settlement.participants.length) * 100)
        : 0
    };

    res.json({
      success: true,
      data: {
        settlement: {
          id: settlement.id,
          status: settlement.status,
          created_at: settlement.created_at,
          completed_at: settlement.completed_at
        },
        statistics
      }
    });
  } catch (error) {
    console.error('정산 통계 조회 오류:', error);
    res.status(500).json({
      success: false,
      message: '정산 통계 조회에 실패했습니다.'
    });
  }
};
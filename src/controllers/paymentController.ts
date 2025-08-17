import { Request, Response } from 'express';
import { TossPaymentService, TossPaymentConfirmRequest, TossPaymentRequest } from '../services/tossPaymentService';
import { SettlementModel } from '../models/settlement';
import { pool } from '../config/database';

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
 * 정산 결제 시작
 */
export const startSettlementPayment = async (req: AuthenticatedRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: '인증이 필요합니다.'
      });
    }

    const { settlementId } = req.body;

    if (!settlementId) {
      return res.status(400).json({
        success: false,
        message: '정산 ID가 필요합니다.'
      });
    }

    const userId = parseInt(req.user!.user_id);

    // 정산 요청 조회
    const settlement = await SettlementModel.getSettlementRequestWithParticipants(settlementId);
    if (!settlement) {
      return res.status(404).json({
        success: false,
        message: '정산 요청을 찾을 수 없습니다.'
      });
    }

    // 사용자의 정산 참여 확인
    const participation = settlement.participants.find(p => p.user_id === userId);
    if (!participation) {
      return res.status(404).json({
        success: false,
        message: '정산 참여 정보를 찾을 수 없습니다.'
      });
    }

    // 이미 결제된 경우 확인
    if (participation.payment_status === 'paid') {
      return res.status(400).json({
        success: false,
        message: '이미 결제가 완료되었습니다.'
      });
    }

    // 기존 orderId가 있으면 재사용, 없으면 새로 생성
    let orderId = participation.toss_order_id;
    if (!orderId) {
      orderId = `settlement_${settlementId}_${userId}_${Date.now()}`;
    }
    
    res.json({
      success: true,
      data: {
        orderId: orderId,
        amount: participation.amount,
        orderName: `정산 결제 - ${settlementId.substring(0, 8)}`,
        settlementId: settlementId
      }
    });

  } catch (error) {
    console.error('정산 결제 시작 오류:', error);
    res.status(500).json({
      success: false,
      message: '결제 시작에 실패했습니다.'
    });
  }
};

/**
 * 정산 결제 승인
 */
export const confirmSettlementPayment = async (req: AuthenticatedRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: '인증이 필요합니다.'
      });
    }

    const { paymentKey, orderId, amount } = req.body;

    if (!paymentKey || !orderId || !amount) {
      return res.status(400).json({
        success: false,
        message: '필수 결제 정보가 누락되었습니다. (paymentKey, orderId, amount)'
      });
    }

    // orderId에서 정산 정보 추출 (settlement_${settlementId}_${userId}_${timestamp})
    const orderIdParts = orderId.split('_');
    if (orderIdParts.length !== 4 || orderIdParts[0] !== 'settlement') {
      return res.status(400).json({
        success: false,
        message: '유효하지 않은 주문 ID입니다.'
      });
    }

    const settlementId = orderIdParts[1];
    const userId = parseInt(orderIdParts[2]);

    if (userId !== parseInt(req.user.user_id)) {
      return res.status(403).json({
        success: false,
        message: '본인의 결제만 승인할 수 있습니다.'
      });
    }

    // 정산 요청 조회
    const settlement = await SettlementModel.getSettlementRequestWithParticipants(settlementId);
    if (!settlement) {
      return res.status(404).json({
        success: false,
        message: '정산 요청을 찾을 수 없습니다.'
      });
    }

    // 사용자의 정산 참여 확인
    const participation = settlement.participants.find(p => p.user_id === userId);
    if (!participation) {
      return res.status(404).json({
        success: false,
        message: '정산 참여 정보를 찾을 수 없습니다.'
      });
    }

    // 금액 검증
    if (participation.amount !== amount) {
      return res.status(400).json({
        success: false,
        message: '결제 금액이 정산 금액과 일치하지 않습니다.'
      });
    }

    // 이미 결제된 경우 확인
    if (participation.payment_status === 'paid') {
      return res.status(400).json({
        success: false,
        message: '이미 결제가 완료되었습니다.'
      });
    }

    const tossPaymentService = new TossPaymentService();
    
    // 토스페이먼츠 결제 승인 요청
    const confirmRequest: TossPaymentConfirmRequest = {
      paymentKey,
      orderId,
      amount
    };

    const paymentResult = await tossPaymentService.confirmPayment(confirmRequest);

    // 결제 상태 업데이트
    const updatedParticipation = await SettlementModel.updateParticipantPaymentStatus(
      participation.id,
      'paid',
      paymentKey,
      orderId
    );

    // 모든 참여자가 결제 완료했는지 확인
    const updatedSettlement = await SettlementModel.getSettlementRequestWithParticipants(settlementId);
    if (updatedSettlement) {
      const allPaid = updatedSettlement.participants.every(p => p.payment_status === 'paid');
      if (allPaid && updatedSettlement.status !== 'completed') {
        await SettlementModel.updateSettlementRequestStatus(settlementId, 'completed');
      }
    }

    res.json({
      success: true,
      message: '결제가 성공적으로 승인되었습니다.',
      data: {
        payment: paymentResult,
        participation: updatedParticipation
      }
    });
  } catch (error: any) {
    console.error('정산 결제 승인 오류:', error);
    
    // 결제 실패 시 상태 업데이트
    try {
      const { orderId } = req.body;
      if (orderId) {
        const orderIdParts = orderId.split('_');
        if (orderIdParts.length === 4 && orderIdParts[0] === 'settlement') {
          const settlementId = orderIdParts[1];
          const userId = parseInt(orderIdParts[2]);
          
          const settlement = await SettlementModel.getSettlementRequestWithParticipants(settlementId);
          if (settlement) {
            const participation = settlement.participants.find(p => p.user_id === userId);
            if (participation) {
              await SettlementModel.updateParticipantPaymentStatus(participation.id, 'failed');
            }
          }
        }
      }
    } catch (updateError) {
      console.error('결제 실패 상태 업데이트 오류:', updateError);
    }

    res.status(500).json({
      success: false,
      message: error.message || '결제 승인에 실패했습니다.'
    });
  }
};

/**
 * 정산 결제 실패 처리
 */
export const handleSettlementPaymentFailure = async (req: AuthenticatedRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: '인증이 필요합니다.'
      });
    }

    const { orderId, errorCode, errorMsg } = req.body;

    if (!orderId) {
      return res.status(400).json({
        success: false,
        message: '주문 ID가 필요합니다.'
      });
    }

    // orderId에서 정산 정보 추출
    const orderIdParts = orderId.split('_');
    if (orderIdParts.length !== 4 || orderIdParts[0] !== 'settlement') {
      return res.status(400).json({
        success: false,
        message: '유효하지 않은 주문 ID입니다.'
      });
    }

    const settlementId = orderIdParts[1];
    const userId = parseInt(orderIdParts[2]);

    if (userId !== parseInt(req.user.user_id)) {
      return res.status(403).json({
        success: false,
        message: '본인의 결제만 처리할 수 있습니다.'
      });
    }

    // 정산 요청 조회
    const settlement = await SettlementModel.getSettlementRequestWithParticipants(settlementId);
    if (!settlement) {
      return res.status(404).json({
        success: false,
        message: '정산 요청을 찾을 수 없습니다.'
      });
    }

    // 사용자의 정산 참여 확인
    const participation = settlement.participants.find(p => p.user_id === userId);
    if (!participation) {
      return res.status(404).json({
        success: false,
        message: '정산 참여 정보를 찾을 수 없습니다.'
      });
    }

    // 결제 실패 상태로 업데이트
    await SettlementModel.updateParticipantPaymentStatus(
      participation.id,
      'failed',
      undefined,
      orderId
    );

    console.log(`정산 결제 실패 처리 완료: ${orderId}, 오류: ${errorCode} - ${errorMsg}`);

    res.json({
      success: true,
      message: '결제 실패가 처리되었습니다.',
      data: {
        orderId,
        errorCode,
        errorMsg
      }
    });
  } catch (error) {
    console.error('정산 결제 실패 처리 오류:', error);
    res.status(500).json({
      success: false,
      message: '결제 실패 처리에 실패했습니다.'
    });
  }
};

/**
 * 결제 정보 조회
 */
export const getPaymentInfo = async (req: Request, res: Response) => {
  try {
    const { paymentKey } = req.params;

    if (!paymentKey) {
      return res.status(400).json({
        success: false,
        message: '결제 키가 필요합니다.'
      });
    }

    const tossPaymentService = new TossPaymentService();
    const paymentInfo = await tossPaymentService.getPayment(paymentKey);

    res.json({
      success: true,
      data: paymentInfo
    });
  } catch (error: any) {
    console.error('결제 정보 조회 오류:', error);
    res.status(500).json({
      success: false,
      message: error.message || '결제 정보 조회에 실패했습니다.'
    });
  }
};

/**
 * 정산 결제 상태 조회
 */
export const getSettlementPaymentStatus = async (req: AuthenticatedRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: '인증이 필요합니다.'
      });
    }

    const { orderId, paymentKey } = req.query;

    if (!orderId || !paymentKey) {
      return res.status(400).json({
        success: false,
        message: 'orderId와 paymentKey가 모두 필요합니다.'
      });
    }

    // orderId에서 정산 정보 추출 (settlement_${settlementId}_${userId}_${timestamp})
    const orderIdParts = (orderId as string).split('_');
    if (orderIdParts.length !== 4 || orderIdParts[0] !== 'settlement') {
      return res.status(400).json({
        success: false,
        message: '유효하지 않은 주문 ID입니다.'
      });
    }

    const settlementId = orderIdParts[1];
    const userId = parseInt(orderIdParts[2]);

    if (userId !== parseInt(req.user.user_id)) {
      return res.status(403).json({
        success: false,
        message: '본인의 결제만 조회할 수 있습니다.'
      });
    }

    // DB에서 정산 정보 조회
    const settlement = await SettlementModel.getSettlementRequestWithParticipants(settlementId);
    if (!settlement) {
      return res.status(404).json({
        success: false,
        message: '정산 요청을 찾을 수 없습니다.'
      });
    }

    const participant = settlement.participants.find(p => p.user_id === userId);
    if (!participant) {
      return res.status(403).json({
        success: false,
        message: '해당 정산에 참여하지 않았습니다.'
      });
    }

    // DB 상태
    console.log('=== DB 결제 상태 ===');
    console.log('orderId:', orderId);
    console.log('participant.id:', participant.id);
    console.log('DB payment_status:', participant.payment_status);
    console.log('DB toss_payment_key:', participant.toss_payment_key);
    console.log('DB paid_at:', participant.paid_at);

    let tossPaymentData = null;
    
    // 토스 API로 실제 상태 확인
    try {
      const tossService = new TossPaymentService();
      tossPaymentData = await tossService.getPayment(paymentKey as string);
        
        console.log('=== 토스 API 응답 ===');
        console.log('전체 응답:', JSON.stringify(tossPaymentData, null, 2));
        console.log('토스 status:', tossPaymentData.status);
        console.log('토스 method:', tossPaymentData.method);
        console.log('토스 approvedAt:', tossPaymentData.approvedAt);
        console.log('토스 amount:', tossPaymentData.totalAmount);
        
    } catch (error) {
      console.log('=== 토스 API 에러 ===');
      console.log('에러:', error);
    }

    // DB 상태와 토스 상태 동기화
    if (tossPaymentData) {
      const tossStatus = tossPaymentData.status;
      const dbStatus = participant.payment_status;
      
      console.log('=== 상태 비교 ===');
      console.log('DB 상태:', dbStatus);
      console.log('토스 상태:', tossStatus);

      // 토스에서 완료되었는데 DB가 pending인 경우 동기화
      if (tossStatus === 'DONE' && dbStatus === 'pending') {
        try {
          const updateQuery = `
            UPDATE settlement_participants 
            SET payment_status = 'paid', 
                toss_payment_key = $1,
                paid_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE settlement_request_id = $2 AND user_id = $3
          `;
          
          await pool.query(updateQuery, [paymentKey, settlementId, userId]);
          console.log('✅ DB 상태를 paid로 동기화 완료');
          
          // participant 객체도 업데이트
          participant.payment_status = 'paid';
          participant.toss_payment_key = paymentKey as string;
          participant.paid_at = new Date();
          
        } catch (syncError) {
          console.error('❌ DB 동기화 실패:', syncError);
        }
      }
    }

    // 응답 반환
    res.json({
      success: true,
      data: {
        orderId: orderId,
        paymentStatus: participant.payment_status, // 최종 상태 (동기화 후)
        amount: participant.amount,
        paidAt: participant.paid_at,
        settlementId: settlementId,
        isPaymentCompleted: participant.payment_status === 'paid'
      }
    });

  } catch (error) {
    console.error('결제 상태 조회 오류:', error);
    res.status(500).json({
      success: false,
      message: '결제 상태 조회에 실패했습니다.'
    });
  }
};

/**
 * 결제 취소
 */
export const cancelPayment = async (req: AuthenticatedRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: '인증이 필요합니다.'
      });
    }

    const { paymentKey } = req.params;
    const { cancelReason, cancelAmount } = req.body;

    if (!paymentKey || !cancelReason) {
      return res.status(400).json({
        success: false,
        message: '결제 키와 취소 사유가 필요합니다.'
      });
    }

    const tossPaymentService = new TossPaymentService();
    const cancelResult = await tossPaymentService.cancelPayment(paymentKey, cancelReason, cancelAmount);

    res.json({
      success: true,
      message: '결제가 성공적으로 취소되었습니다.',
      data: cancelResult
    });
  } catch (error: any) {
    console.error('결제 취소 오류:', error);
    res.status(500).json({
      success: false,
      message: error.message || '결제 취소에 실패했습니다.'
    });
  }
};
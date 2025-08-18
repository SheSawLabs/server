import { pool } from '../config/database';
import { TossPaymentService } from '../services/tossPaymentService';

export interface SettlementRequest {
  id: string;
  post_id: string;
  creator_id: number;
  total_amount: number;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  created_at: Date;
  updated_at: Date;
  completed_at?: Date;
}

export interface SettlementParticipant {
  id: string;
  settlement_request_id: string;
  user_id: number;
  amount: number;
  payment_status: 'pending' | 'paid' | 'failed' | 'refunded';
  toss_payment_key?: string;
  toss_order_id?: string;
  paid_at?: Date;
  created_at: Date;
  updated_at: Date;
  nickname?: string;
  profile_image?: string;
}

export interface CreateSettlementRequest {
  post_id: string;
  creator_id: number;
  total_amount: number;
  participants: {
    user_id: number;
    amount: number;
  }[];
}

export interface SettlementRequestWithParticipants extends SettlementRequest {
  participants: SettlementParticipant[];
  post_title?: string;
  post_category?: string;
}

export class SettlementModel {
  /**
   * 정산 요청 생성
   */
  static async createSettlementRequest(data: CreateSettlementRequest): Promise<SettlementRequestWithParticipants> {
    const client = await pool.connect();
    
    try {
      await client.query('BEGIN');
      
      // 참여자들의 금액 합계가 총 금액과 일치하는지 확인
      const participantsTotal = data.participants.reduce((sum, p) => sum + p.amount, 0);
      if (participantsTotal !== data.total_amount) {
        throw new Error('참여자들의 금액 합계가 총 금액과 일치하지 않습니다.');
      }
      
      // 정산 요청 생성
      const settlementRequestQuery = `
        INSERT INTO settlement_requests (post_id, creator_id, total_amount)
        VALUES ($1, $2, $3)
        RETURNING *
      `;
      
      const settlementResult = await client.query(settlementRequestQuery, [
        data.post_id,
        data.creator_id,
        data.total_amount
      ]);
      
      const settlementRequest = settlementResult.rows[0];
      
      // 정산 참여자들 생성
      const participants: SettlementParticipant[] = [];
      for (const participant of data.participants) {
        // toss_order_id 미리 생성
        const tossOrderId = TossPaymentService.generateSettlementOrderId(settlementRequest.id, participant.user_id);
        
        const participantQuery = `
          INSERT INTO settlement_participants (settlement_request_id, user_id, amount, toss_order_id)
          VALUES ($1, $2, $3, $4)
          RETURNING *
        `;
        
        const participantResult = await client.query(participantQuery, [
          settlementRequest.id,
          participant.user_id,
          participant.amount,
          tossOrderId
        ]);
        
        participants.push(this.mapDbRowToParticipant(participantResult.rows[0]));
      }
      
      await client.query('COMMIT');
      
      return {
        ...this.mapDbRowToSettlementRequest(settlementRequest),
        participants
      };
    } catch (error) {
      await client.query('ROLLBACK');
      console.error('정산 요청 생성 실패:', error);
      throw error;
    } finally {
      client.release();
    }
  }
  
  /**
   * 정산 요청 조회 (참여자 포함)
   */
  static async getSettlementRequestWithParticipants(settlementId: string): Promise<SettlementRequestWithParticipants | null> {
    try {
      const settlementQuery = `
        SELECT * FROM settlement_requests WHERE id = $1
      `;
      const settlementResult = await pool.query(settlementQuery, [settlementId]);
      
      if (settlementResult.rows.length === 0) {
        return null;
      }
      
      const participantsQuery = `
        SELECT sp.*, u.nickname as user_name
        FROM settlement_participants sp
        LEFT JOIN users u ON sp.user_id = u.id
        WHERE sp.settlement_request_id = $1
      `;
      const participantsResult = await pool.query(participantsQuery, [settlementId]);
      
      return {
        ...this.mapDbRowToSettlementRequest(settlementResult.rows[0]),
        participants: participantsResult.rows.map(row => this.mapDbRowToParticipant(row))
      };
    } catch (error) {
      console.error('정산 요청 조회 실패:', error);
      throw new Error('정산 요청 조회에 실패했습니다.');
    }
  }
  
  /**
   * 특정 게시물의 정산 요청 목록 조회
   */
  static async getSettlementRequestsByPostId(postId: string): Promise<SettlementRequest[]> {
    try {
      const query = `
        SELECT * FROM settlement_requests 
        WHERE post_id = $1 
        ORDER BY created_at DESC
      `;
      const result = await pool.query(query, [postId]);
      
      return result.rows.map(row => this.mapDbRowToSettlementRequest(row));
    } catch (error) {
      console.error('게시물 정산 요청 목록 조회 실패:', error);
      throw new Error('정산 요청 목록 조회에 실패했습니다.');
    }
  }

  /**
   * 특정 게시물의 정산 상세 정보 조회 (참여자 포함)
   */
  static async getSettlementByPostId(postId: string): Promise<SettlementRequestWithParticipants | null> {
    try {
      const settlementQuery = `
        SELECT * FROM settlement_requests 
        WHERE post_id = $1 
        ORDER BY created_at DESC 
        LIMIT 1
      `;
      const settlementResult = await pool.query(settlementQuery, [postId]);
      
      if (settlementResult.rows.length === 0) {
        return null;
      }
      
      const settlement = settlementResult.rows[0];
      
      const participantsQuery = `
        SELECT sp.*, u.nickname as user_name, u.profile_image
        FROM settlement_participants sp
        LEFT JOIN users u ON sp.user_id = u.id
        WHERE sp.settlement_request_id = $1
      `;
      const participantsResult = await pool.query(participantsQuery, [settlement.id]);
      
      return {
        ...this.mapDbRowToSettlementRequest(settlement),
        participants: participantsResult.rows.map(row => this.mapDbRowToParticipant(row))
      };
    } catch (error) {
      console.error('게시물 정산 상세 조회 실패:', error);
      throw new Error('정산 상세 조회에 실패했습니다.');
    }
  }
  
  /**
   * 사용자의 정산 참여 목록 조회 (결제해야 할 목록)
   */
  static async getSettlementParticipationsByUserId(userId: number): Promise<SettlementRequestWithParticipants[]> {
    try {
      const query = `
        SELECT sr.*, sp.amount as participant_amount, sp.payment_status, sp.toss_payment_key, sp.toss_order_id, sp.paid_at,
               p.title as post_title, p.category as post_category
        FROM settlement_requests sr
        JOIN settlement_participants sp ON sr.id = sp.settlement_request_id
        LEFT JOIN posts p ON sr.post_id = p.id
        WHERE sp.user_id = $1
        ORDER BY sr.created_at DESC
      `;
      const result = await pool.query(query, [userId]);
      
      const settlementMap = new Map<string, SettlementRequestWithParticipants>();
      
      for (const row of result.rows) {
        const settlementId = row.id;
        
        if (!settlementMap.has(settlementId)) {
          settlementMap.set(settlementId, {
            ...this.mapDbRowToSettlementRequest(row),
            participants: []
          });
        }
        
        const settlement = settlementMap.get(settlementId)!;
        // 포스트 정보 추가
        settlement.post_title = row.post_title;
        settlement.post_category = row.post_category;
        
        settlement.participants.push({
          id: row.settlement_participant_id,
          settlement_request_id: settlementId,
          user_id: userId,
          amount: row.participant_amount,
          payment_status: row.payment_status,
          toss_payment_key: row.toss_payment_key,
          toss_order_id: row.toss_order_id,
          paid_at: row.paid_at ? new Date(row.paid_at) : undefined,
          created_at: new Date(row.created_at),
          updated_at: new Date(row.updated_at)
        });
      }
      
      return Array.from(settlementMap.values());
    } catch (error) {
      console.error('사용자 정산 참여 목록 조회 실패:', error);
      throw new Error('정산 참여 목록 조회에 실패했습니다.');
    }
  }
  
  /**
   * 정산 참여자의 결제 상태 업데이트
   */
  static async updateParticipantPaymentStatus(
    participantId: string,
    paymentStatus: 'pending' | 'paid' | 'failed' | 'refunded',
    tossPaymentKey?: string,
    tossOrderId?: string
  ): Promise<SettlementParticipant> {
    try {
      const query = `
        UPDATE settlement_participants 
        SET payment_status = $1, 
            toss_payment_key = $2, 
            toss_order_id = $3,
            paid_at = CASE WHEN $1 = 'paid' THEN CURRENT_TIMESTAMP ELSE paid_at END
        WHERE id = $4
        RETURNING *
      `;
      
      const result = await pool.query(query, [paymentStatus, tossPaymentKey, tossOrderId, participantId]);
      
      if (result.rows.length === 0) {
        throw new Error('정산 참여자를 찾을 수 없습니다.');
      }
      
      return this.mapDbRowToParticipant(result.rows[0]);
    } catch (error) {
      console.error('결제 상태 업데이트 실패:', error);
      throw error;
    }
  }
  
  /**
   * 정산 요청 상태 업데이트
   */
  static async updateSettlementRequestStatus(
    settlementId: string,
    status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  ): Promise<SettlementRequest> {
    try {
      const query = `
        UPDATE settlement_requests 
        SET status = $1,
            completed_at = CASE WHEN $1 = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
        WHERE id = $2
        RETURNING *
      `;
      
      const result = await pool.query(query, [status, settlementId]);
      
      if (result.rows.length === 0) {
        throw new Error('정산 요청을 찾을 수 없습니다.');
      }
      
      return this.mapDbRowToSettlementRequest(result.rows[0]);
    } catch (error) {
      console.error('정산 요청 상태 업데이트 실패:', error);
      throw error;
    }
  }
  
  /**
   * DB 행을 SettlementRequest 객체로 변환
   */
  private static mapDbRowToSettlementRequest(row: any): SettlementRequest {
    return {
      id: row.id,
      post_id: row.post_id,
      creator_id: row.creator_id,
      total_amount: row.total_amount,
      status: row.status,
      created_at: new Date(row.created_at),
      updated_at: new Date(row.updated_at),
      completed_at: row.completed_at ? new Date(row.completed_at) : undefined
    };
  }
  
  /**
   * DB 행을 SettlementParticipant 객체로 변환
   */
  private static mapDbRowToParticipant(row: any): SettlementParticipant & { nickname?: string } {
    return {
      id: row.id,
      settlement_request_id: row.settlement_request_id,
      user_id: row.user_id,
      amount: row.amount,
      payment_status: row.payment_status,
      toss_payment_key: row.toss_payment_key,
      toss_order_id: row.toss_order_id,
      paid_at: row.paid_at ? new Date(row.paid_at) : undefined,
      created_at: new Date(row.created_at),
      updated_at: new Date(row.updated_at),
      nickname: row.user_name,
    };
  }

}
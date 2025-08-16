import axios from 'axios';

export interface TossPaymentRequest {
  amount: number;
  orderId: string;
  orderName: string;
  customerName?: string;
  customerEmail?: string;
  successUrl: string;
  failUrl: string;
}

export interface TossPaymentResponse {
  mId: string;
  lastTransactionKey?: string;
  paymentKey: string;
  orderId: string;
  orderName: string;
  taxExemptionAmount: number;
  status: string;
  requestedAt: string;
  approvedAt?: string;
  useEscrow: boolean;
  cultureExpense: boolean;
  card?: any;
  virtualAccount?: any;
  transfer?: any;
  mobilePhone?: any;
  giftCertificate?: any;
  cashReceipt?: any;
  cashReceipts?: any;
  discount?: any;
  cancels?: any;
  secret?: string;
  type: string;
  easyPay?: any;
  country: string;
  failure?: any;
  isPartialCancelable: boolean;
  receipt: {
    url: string;
  };
  checkout: {
    url: string;
  };
  currency: string;
  totalAmount: number;
  balanceAmount: number;
  suppliedAmount: number;
  vat: number;
  taxFreeAmount: number;
  method: string;
  version: string;
}

export interface TossPaymentConfirmRequest {
  paymentKey: string;
  orderId: string;
  amount: number;
}

export class TossPaymentService {
  private readonly baseUrl: string;
  private readonly secretKey: string;
  
  constructor() {
    // 환경에 따라 테스트/실서버 URL 구분
    this.baseUrl = process.env.NODE_ENV === 'production' 
      ? 'https://api.tosspayments.com' 
      : 'https://api.tosspayments.com';
    
    this.secretKey = process.env.NODE_ENV === 'production'
      ? process.env.TOSS_SECRET_KEY || ''
      : process.env.TOSS_TEST_SECRET_KEY || '';
    
    if (!this.secretKey) {
      throw new Error('토스페이먼츠 시크릿 키가 설정되지 않았습니다.');
    }
  }
  
  /**
   * 결제 승인 요청
   */
  async confirmPayment(confirmData: TossPaymentConfirmRequest): Promise<TossPaymentResponse> {
    try {
      const headers = {
        'Authorization': `Basic ${Buffer.from(this.secretKey + ':').toString('base64')}`,
        'Content-Type': 'application/json'
      };
      
      const response = await axios.post(
        `${this.baseUrl}/v1/payments/confirm`,
        confirmData,
        { headers }
      );
      
      return response.data;
    } catch (error: any) {
      console.error('토스페이먼츠 결제 승인 실패:', error.response?.data || error.message);
      
      if (error.response?.data) {
        throw new Error(`결제 승인 실패: ${error.response.data.message || '알 수 없는 오류'}`);
      }
      
      throw new Error('결제 승인 중 오류가 발생했습니다.');
    }
  }
  
  /**
   * 결제 조회
   */
  async getPayment(paymentKey: string): Promise<TossPaymentResponse> {
    try {
      const headers = {
        'Authorization': `Basic ${Buffer.from(this.secretKey + ':').toString('base64')}`
      };
      
      const response = await axios.get(
        `${this.baseUrl}/v1/payments/${paymentKey}`,
        { headers }
      );
      
      return response.data;
    } catch (error: any) {
      console.error('토스페이먼츠 결제 조회 실패:', error.response?.data || error.message);
      throw new Error('결제 정보 조회에 실패했습니다.');
    }
  }
  
  /**
   * 결제 취소
   */
  async cancelPayment(paymentKey: string, cancelReason: string, cancelAmount?: number): Promise<TossPaymentResponse> {
    try {
      const headers = {
        'Authorization': `Basic ${Buffer.from(this.secretKey + ':').toString('base64')}`,
        'Content-Type': 'application/json'
      };
      
      const cancelData: any = {
        cancelReason
      };
      
      if (cancelAmount) {
        cancelData.cancelAmount = cancelAmount;
      }
      
      const response = await axios.post(
        `${this.baseUrl}/v1/payments/${paymentKey}/cancel`,
        cancelData,
        { headers }
      );
      
      return response.data;
    } catch (error: any) {
      console.error('토스페이먼츠 결제 취소 실패:', error.response?.data || error.message);
      throw new Error('결제 취소에 실패했습니다.');
    }
  }
  
  /**
   * 결제 시작 (결제 페이지 URL 반환)
   */
  async createPayment(paymentRequest: TossPaymentRequest): Promise<{ checkoutUrl: string }> {
    try {
      const headers = {
        'Authorization': `Basic ${Buffer.from(this.secretKey + ':').toString('base64')}`,
        'Content-Type': 'application/json'
      };
      
      const response = await axios.post(
        `${this.baseUrl}/v1/payments`,
        paymentRequest,
        { headers }
      );
      
      return {
        checkoutUrl: response.data.checkout.url
      };
    } catch (error: any) {
      console.error('토스페이먼츠 결제 생성 실패:', error.response?.data || error.message);
      throw new Error('결제 생성에 실패했습니다.');
    }
  }

  /**
   * 주문 ID 생성 (정산 전용)
   */
  static generateSettlementOrderId(settlementId: string, userId: number): string {
    const timestamp = Date.now();
    return `settlement_${settlementId}_${userId}_${timestamp}`;
  }
  
  /**
   * 결제 금액 검증
   */
  static validateAmount(amount: number): boolean {
    return amount > 0 && amount <= 10000000; // 최대 1천만원
  }
}
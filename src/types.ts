export interface Coordinates {
  lat: number;
  lng: number;
}

export interface Facilities {
  cctv: number;
  streetlight: number;
  police_station: number;
  safety_house: number;
  delivery_box: number;
}

export interface RiskFactors {
  sexual_offender: number;
}

export interface DongData {
  dong_code: string;
  district: string;
  dong: string;
  grade: 'A' | 'B' | 'C' | 'D' | 'E';
  score: number;
  coordinates: Coordinates;
  facilities: Facilities;
  risk_factors: RiskFactors;
}

export interface GradeDistribution {
  A: number;
  B: number;
  C: number;
  D: number;
  E: number;
}

export interface MapDataMetadata {
  title: string;
  description: string;
  generated_at: string;
  total_dong: number;
  grade_distribution: GradeDistribution;
}

export interface MapData {
  metadata: MapDataMetadata;
  data: DongData[];
}

export interface CPTEDPrinciple {
  name: string;
  weight: string;
  description: string;
  factors: string[];
}

export interface CPTEDPrinciples {
  natural_surveillance: CPTEDPrinciple;
  access_control: CPTEDPrinciple;
  territoriality: CPTEDPrinciple;
  maintenance: CPTEDPrinciple;
  activity_support: CPTEDPrinciple;
}

export interface ReportDataMetadata {
  title: string;
  description: string;
  generated_at: string;
  total_dong: number;
  cpted_principles: CPTEDPrinciples;
}

export interface ReportData {
  metadata: ReportDataMetadata;
  analysis: any;
}

// Auth related types
export interface AuthResponse {
  success: boolean;
  message: string;
  data?: {
    access_token?: string;
    refresh_token?: string;
    token?: string; // legacy support
    user: User;
  };
  error?: string;
}

export interface AuthTokenPayload {
  user_id: string;
  email: string;
  nickname?: string;
  provider?: string;
  providerId?: string;
  iat: number;
  exp: number;
}

// User types
export interface User {
  id: string;
  kakao_id: string;
  email: string;
  nickname: string;
  profile_image?: string;
  created_at: Date;
  updated_at: Date;
  provider?: string;
  providerId?: string;
}

export interface KakaoUserInfo {
  id: number;
  connected_at: string;
  properties: {
    nickname: string;
    profile_image?: string;
    thumbnail_image?: string;
  };
  kakao_account: {
    profile_nickname_needs_agreement: boolean;
    profile_image_needs_agreement: boolean;
    profile: {
      nickname: string;
      thumbnail_image_url?: string;
      profile_image_url?: string;
      is_default_image: boolean;
    };
    has_email: boolean;
    email_needs_agreement: boolean;
    is_email_valid: boolean;
    is_email_verified: boolean;
    email: string;
  };
  // Additional properties for easier access
  email?: string;
  nickname?: string;
  profileImage?: string;
  thumbnailImage?: string;
}

export interface KakaoTokenResponse {
  access_token: string;
  token_type: string;
  refresh_token: string;
  expires_in: number;
  scope: string;
  refresh_token_expires_in: number;
}
export interface Review {
  id?: number;
  user_id?: number;
  title?: string;
  content?: string;
  author?: string;
  rating: number;
  location?: string;
  reviewText?: string;
  timeOfDay?: string;
  selectedKeywords?: any[];
  recommendedKeywords?: any[];
  scoreResult?: any;
  contextAnalysis?: any;
  analysisMethod?: string;
  safety_score?: number;
  environmental_score?: number;
  accessibility_score?: number;
  natural_surveillance?: number;
  access_control?: number;
  territoriality?: number;
  maintenance?: number;
  created_at?: Date;
  updated_at?: Date;
  createdAt?: Date;
  updatedAt?: Date;
}

export interface AnalysisResult {
  safety_score: number;
  environmental_score: number;
  accessibility_score: number;
  natural_surveillance: number;
  access_control: number;
  territoriality: number;
  maintenance: number;
  analysis_summary: string;
  recommendations: string[];
}

export interface RestrictedAnalysis {
  restricted_score: number;
  safety_issues: string[];
  risk_factors: string[];
  recommendations: string[];
  severity_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export interface ReviewStats {
  totalReviews: number;
  averageRating?: number;
  averageSafetyScore?: number;
  averageEnvironmentalScore?: number;
  averageAccessibilityScore?: number;
  averageNaturalSurveillance?: number;
  averageAccessControl?: number;
  averageTerritoriality?: number;
  averageMaintenance?: number;
  reviewsByRating?: { [key: number]: number };
  recentReviews?: Review[];
  keywordUsage?: { [key: string]: number };
  categoryUsage?: { [key: string]: number };
  averageScore?: number;
  safetyLevelDistribution?: { [key: string]: number };
  analysisMethodDistribution?: { [key: string]: number };
  keywordSelectionStats?: {
    totalUsers: number;
    keywordSelections: { [keyword: string]: { count: number; percentage: number } };
    categorySelections: { [category: string]: { count: number; percentage: number } };
  };
}
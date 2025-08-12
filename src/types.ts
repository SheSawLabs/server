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

export interface StreetLight {
  id: number;
  management_number: string;
  district: string;
  dong: string;
  latitude: number;
  longitude: number;
}

export interface StreetLightByDong {
  dong: string;
  district: string;
  count: number;
  streetlights: StreetLight[];
}
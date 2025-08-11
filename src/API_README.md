# CPTED Review Analyzer API 문서

## 개요
CPTED(Crime Prevention Through Environmental Design) 원리를 기반으로 한 리뷰 분석 시스템 API입니다.

## 기본 정보
- **Base URL**: `http://localhost:3000`
- **Content-Type**: `application/json`

## 사용자 참여 방식 (부담도 순)

### 1단계: 최간단 참여 ⭐
**별점(1-5) + 키워드 1-2개만 선택**
```bash
POST /api/restricted/analyze-keywords
{
  "selectedKeywords": [
    {"category": "감정형", "keyword": "안심"}
  ],
  "rating": 4,
  "location": "강남구 역삼동"
}
```

### 2단계: 일반 참여 ⭐⭐
**별점 + 키워드 + 한줄 소감(선택)**
```bash
POST /api/review/analyze-keywords-rating
{
  "selectedKeywords": [
    {"category": "자연적 감시", "keyword": "밝음"},
    {"category": "감정형", "keyword": "안심"}
  ],
  "rating": 4,
  "reviewText": "가로등이 많아서 밝고 안전해요",
  "location": "강남구 역삼동"
}
```

### 3단계: 상세 참여 ⭐⭐⭐
**별점 + 키워드 + 긴 리뷰 텍스트**
```bash
POST /api/restricted/analyze-restricted
{
  "reviewText": "밤에 이 길을 걸으면 가로등이 부족해서 너무 어둡고 무서워요.",
  "location": "강남구 역삼동",
  "timeOfDay": "밤",
  "rating": 2
}
```

## 키워드 카테고리

| **CPTED 영역** | **키워드** | **설명** |
|---|---|---|
| **자연적 감시** | 밝음, 어두움, 시야트임 | 밤길 밝기, 시야 확보 여부 |
| **자연적 접근 통제** | 한적, 복잡, 골목많음 | 동네 개방감 |
| **영역성 강화** | 어수선, 깔끔, 방치됨 | 동네가 관리되고 있는 느낌 |
| **활동 활성화** | 주요상권있음, 공원있음 | 사람 왕래, 활동성 여부 |
| **유지관리** | 깨끗, 쓰레기많음, 방치 | 환경 관리 상태 |
| **감정형** | 안심, 약간불안, 불안, 위험 | 체감 안전도 |

## 주요 API 엔드포인트

### 시스템 정보
```bash
GET /api/restricted/system-info
```
사용 가능한 키워드 목록과 시스템 정보를 조회합니다.

### 키워드 추천
```bash
POST /api/restricted/recommend-keywords
{
  "reviewText": "공원 근처라서 사람들이 많이 다니고 밝아서 안전해 보여요.",
  "location": "강남구 역삼동"
}
```
텍스트 분석을 통해 적절한 키워드를 추천합니다.

## 응답 형태

### 성공 응답
```json
{
  "success": true,
  "method": "restricted",
  "data": {
    "scoreResult": {
      "totalScore": 91,
      "grade": "A",
      "rating": 4
    },
    "recommendedKeywords": [
      {
        "category": "자연적 감시",
        "keyword": "밝음",
        "confidence": 0.9,
        "source": "public_data"
      }
    ],
    "contextAnalysis": {
      "locationContext": {
        "district": "강남구",
        "dong": "역삼동",
        "safetyGrade": "B",
        "facilities": {
          "cctv": 15,
          "streetlight": 89
        }
      }
    }
  }
}
```

## 점수 및 등급 시스템

### 별점 기반 점수
- 1점 = 20점 기본값
- 2점 = 40점 기본값  
- 3점 = 60점 기본값
- 4점 = 80점 기본값
- 5점 = 100점 기본값

### 등급 시스템
- **A등급**: 80점 이상 (매우 안전)
- **B등급**: 70-79점 (안전)  
- **C등급**: 60-69점 (보통)
- **D등급**: 50-59점 (주의 필요)
- **E등급**: 50점 미만 (위험)

## 데이터 소스

### 1. AI 기반 분석
- **GROQ API** 사용으로 텍스트의 감정과 상황 분석
- 자연어 처리를 통한 키워드 추출 및 추천

### 2. 키워드 매칭 기반
- **18개 사전 정의 키워드**와 동의어 매칭
- 부정 표현 감지 ("밝지 않다" → "어두움")

### 3. 공공데이터 기반  
- **서울시 동별 안전도 데이터** (50개 동)
- 실제 CCTV, 가로등, 경찰서, 성범죄자 수 등 반영
- 위치 기반 맞춤형 키워드 추천

## 환경 설정

### 필수 환경 변수 (.env)
```bash
# AI API
GROQ_API_KEY=your_groq_api_key_here
DISABLE_AI=false

# Database  
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cpted_analyzer_db
DB_USER=postgres
DB_PASSWORD=password

# Server
PORT=3000
NODE_ENV=development
```

## 실행 방법

```bash
# 의존성 설치
npm install

# 빌드
npm run build

# 서버 실행
npm start

# 개발 모드 (자동 재시작)
npm run dev
```

## 데이터베이스 설정

PostgreSQL 데이터베이스가 필요하며, Docker로 쉽게 설정할 수 있습니다:

```bash
# Docker 컨테이너로 실행
docker-compose up -d

# 또는 로컬 PostgreSQL 사용
psql -U postgres -c "CREATE DATABASE cpted_analyzer_db;"
```

## API 테스트 예시

### 간단한 별점+키워드 참여
```bash
curl -X POST http://localhost:3000/api/restricted/analyze-keywords \
  -H "Content-Type: application/json" \
  -d '{
    "selectedKeywords": [{"category": "감정형", "keyword": "안심"}],
    "rating": 4,
    "location": "강남구 역삼동"
  }'
```

### AI 기반 키워드 추천
```bash
curl -X POST http://localhost:3000/api/review/recommend-keywords \
  -H "Content-Type: application/json" \
  -d '{
    "reviewText": "이 동네는 깔끔하고 깨끗해서 좋아요. 상권도 발달해있어요."
  }'
```

---

*CPTED Review Analyzer v1.0.0*
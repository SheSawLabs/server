# Seoul Safety Data Pipeline 🏙️🔒

> **서울시 안전 데이터 수집 및 관리 파이프라인**  
> 다양한 공공 API로부터 서울시 안전 관련 데이터를 수집하고 통합 관리하는 시스템

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)

## 🎯 프로젝트 개요

서울시의 안전 관련 시설 정보를 공공 API로부터 자동으로 수집하고, CPTED(Crime Prevention Through Environmental Design) 원칙에 기반한 동별 안전도 분석 시스템입니다.

### 📊 수집 대상 데이터

| 데이터 유형 | 설명 | 현재 상태 |
|------------|------|-----------|
| 🚔 **경찰서/지구대/파출소** | 서울시 경찰 시설 243개소 | ✅ 완료 |
| 💡 **가로등** | 서울시 가로등 설치 현황 | ✅ 완료 |
| 🏠 **여성안심지킴이집** | 여성 안전 보호 시설 | ✅ 완료 |
| ⚠️ **성범죄자 거주지** | 공개된 성범죄자 주소 정보 | ✅ 완료 |
| 📹 **CCTV** | 서울시 CCTV 설치 현황 | ✅ 완료 |
| 📦 **안심택배함** | 안전한 택배 수령 시설 | ✅ 완료 |
| 🔒 **동별 안전도** | CPTED 기반 안전도 분석 | ✅ 완료 |

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   공공 API      │────│  Data Pipeline  │────│   PostgreSQL    │
│                 │    │                 │    │                 │
│ • 서울 열린데이터│    │ • 컨트롤러       │    │ • 통합 저장     │
│ • 공공데이터포털 │    │ • 스케줄러       │    │ • 지오코딩 보강  │
│ • ODCloud API   │    │ • 지오코딩       │    │ • 인덱싱 최적화  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 주요 기능

### 1. 데이터 수집 컨트롤러
- **자동화된 API 호출**: 각 데이터 소스별 전용 컨트롤러
- **에러 처리**: 재시도 로직 및 예외 상황 대응
- **배치 처리**: 대용량 데이터 효율적 처리
- **중복 제거**: UPSERT 방식으로 데이터 무결성 보장

### 2. 지오코딩 시스템
- **주소 → 좌표 변환**: Kakao Local API 활용
- **좌표 → 주소 변환**: 역지오코딩 지원
- **주소 파싱**: 구/동 정보 자동 추출
- **좌표 검증**: 대한민국 영역 내 좌표 확인

### 3. CPTED 기반 안전도 분석
- **5개 원칙 적용**: 자연적 감시(35%), 접근통제(25%), 영역성(20%), 유지관리(10%), 활동성(10%)
- **동별 안전도 등급**: A~E 등급으로 분류
- **시설 밀도 분석**: 면적 대비 안전 시설 밀도 계산
- **개선 권고**: 부족한 시설에 대한 구체적 개선 방안 제시

### 4. JSON 데이터 출력
- **지도 표시용 데이터**: 동별 요약 정보 및 좌표
- **상세 리포트**: CPTED 분석 결과 및 시설별 세부 정보

### 5. 스케줄러
- **자동 수집**: 정기적인 데이터 업데이트
- **API 제한 관리**: 일일 호출 한도 준수
- **로깅**: 상세한 실행 로그 및 통계

## 📁 프로젝트 구조

```
seoul-safety-data-pipeline/
├── controllers/                 # 데이터 수집 컨트롤러
│   ├── streetlight_controller.py
│   ├── police_station_controller.py
│   ├── female_safety_house_controller.py
│   ├── sexual_offender_controller.py
│   ├── cctv_controller.py
│   ├── delivery_box_controller.py
│   └── safety_analysis_controller.py
├── safety_score/               # 안전도 분석 시스템
│   ├── cpted_calculator.py     # CPTED 기반 안전도 계산
│   └── dong_safety_calculator.py # 동별 안전도 통합 분석
├── analysis/                   # 분석 및 리포트 생성
│   ├── safety_analyzer.py
│   ├── report_generator.py
│   └── detailed_report_generator.py
├── scripts/                    # 데이터 생성 스크립트
│   ├── generate_map_data.py    # 지도용 JSON 생성
│   ├── generate_report_data.py # 상세 리포트 JSON 생성
│   ├── geocoding.py
│   ├── parse_csv.py
│   └── assign_dong.py
├── data/                       # 생성된 JSON 데이터
│   ├── map_data.json          # 지도 표시용 동별 요약 데이터
│   └── report_data.json       # 동별 상세 안전도 리포트
├── scheduler/                   # 스케줄링 시스템
│   ├── streetlight_scheduler.py
│   └── sexual_offender_scheduler.py
├── utils/                      # 유틸리티 모듈
│   ├── api_utils.py
│   ├── geocoding.py
│   ├── address_parser.py
│   ├── data_go_kr_api.py
│   └── odcloud_api.py
├── db/                        # 데이터베이스 관련
│   ├── db_connection.py
│   ├── init_schema.py
│   └── schemas/               # SQL 스키마 정의
├── archive_temp_files/         # 개발 중 임시 파일들
├── config/                    # 설정 파일
│   └── settings.py
├── docker-compose.yml         # Docker 구성
├── Dockerfile
└── requirements.txt
```

## 🛠️ 설치 및 실행

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/SheSawLabs/server.git
cd server

# 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 설정 필요
```

### 2. Docker로 실행 (권장)

```bash
# 데이터베이스 및 애플리케이션 실행
docker compose up -d

# 개발 환경 실행
docker compose --profile dev up -d dev
```

### 3. 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# PostgreSQL 데이터베이스 준비 후
python main.py
```

## 🔑 API 키 설정

`.env` 파일에 다음 API 키들을 설정해야 합니다:

```env
# 카카오 로컬 API (지오코딩)
KAKAO_API_KEY=your_kakao_api_key

# 서울 열린데이터광장
SEOUL_OPEN_API_KEY=your_seoul_open_api_key

# 공공데이터포털 API 키들
SEXUAL_OFFENDER_API_KEY=your_sexual_offender_api_key
SEOUL_STREETLIGHT_API_KEY=your_streetlight_api_key
WOMEN_SAFETY_API_KEY=your_women_safety_api_key
```

## 📊 데이터베이스 스키마

각 안전 시설별로 최적화된 테이블 구조:

- `police_stations` - 경찰서/지구대/파출소 정보
- `streetlight_installations` - 가로등 설치 현황
- `female_safety_houses` - 여성안심지킴이집
- `sexual_offender_addresses` - 성범죄자 거주지 정보
- `cctv_installations` - CCTV 설치 현황
- `safe_delivery_boxes` - 안심택배함 위치
- `dong_safety_scores` - 동별 CPTED 기반 안전도 점수 및 등급

## 🎯 사용 예시

### 1. 개별 컨트롤러 실행
```bash
# 경찰서 데이터 수집
docker exec shesaw_dev python3 controllers/police_station_controller.py

# 가로등 데이터 수집
docker exec shesaw_dev python3 controllers/streetlight_controller.py
```

### 2. 안전도 분석 실행
```bash
# 동별 안전도 계산
docker exec shesaw_dev python3 safety_score/dong_safety_calculator.py
```

### 3. JSON 데이터 생성
```bash
# 지도용 동별 요약 데이터 생성
docker exec shesaw_dev python3 scripts/generate_map_data.py

# 동별 상세 리포트 데이터 생성
docker exec shesaw_dev python3 scripts/generate_report_data.py
```

### 4. 스케줄러 실행
```bash
# 정기 수집 스케줄러 실행
docker exec shesaw_dev python3 scheduler/streetlight_scheduler.py
```

## 📈 성과

- **✅ 완료된 데이터 수집**
  - 서울시 경찰서 243개소 수집 완료
  - 가로등 설치 현황 데이터 수집 완료
  - 여성안심지킴이집 데이터 수집 완료
  - 성범죄자 거주지 정보 수집 완료
  - CCTV 및 안심택배함 데이터 수집 완료

- **🔒 안전도 분석 시스템**
  - CPTED 5개 원칙 기반 동별 안전도 계산 완료
  - 서울시 전 동(약 400여개) 안전도 등급 분류
  - 지도 표시용 JSON 데이터 생성 (`data/map_data.json`)
  - 상세 분석 리포트 JSON 생성 (`data/report_data.json`)

- **🔧 기술적 성과**
  - 안정적인 API 연동 시스템 구축
  - 효율적인 지오코딩 파이프라인 구현
  - Docker 기반 컨테이너화 완료
  - 확장 가능한 아키텍처 설계
  - 실시간 안전도 분석 및 JSON 출력 시스템

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 개발팀

- **SheSaw Labs** - *Initial work* - [SheSawLabs](https://github.com/SheSawLabs)
- **Claude (Anthropic)** - *AI Assistant & Code Collaboration*

---

> 💡 **이 프로젝트는 Claude AI와의 협업으로 개발되었습니다.**  
> 인공지능과 인간의 협력으로 만들어진 실용적인 공공 데이터 파이프라인입니다.

# Seoul Safety Data Pipeline - Docker 실행 가이드

## 🐳 Docker로 실행하기

### 1. 환경 설정

**.env 파일 생성:**
```bash
# .env 파일 생성하고 API 키 입력
nano .env
```

**.env 파일 예시:**
```bash
# API Keys (실제 키로 교체)
SEOUL_OPEN_API_KEY=your_seoul_open_api_key_here
KAKAO_API_KEY=your_kakao_api_key_here

# Database (Docker에서 자동 설정)
DB_HOST=shesaw
DB_PORT=5432
DB_NAME=seoul_safety
DB_USER=shesaw
DB_PASSWORD=실제비밀번호로교체
```

### 2. Docker 실행

**테스트 모드:**
```bash
docker-compose up --build
```

**실제 데이터 수집:**
```bash
# 데이터베이스 초기화 + CCTV 데이터 수집
docker-compose run --rm app python main.py --init-db --data-types cctv
```

**개발 모드 (코드 수정하면서 테스트):**
```bash
# 개발 모드 실행
docker-compose --profile dev up -d

# 컨테이너 접속
docker-compose exec dev bash

# 컨테이너 내부에서 자유롭게 실행
python main.py --test
python controllers/cctv_controller.py
```

### 3. 유용한 명령어

```bash
# 로그 확인
docker-compose logs app

# 데이터베이스 접속
docker-compose exec postgres psql -U postgres -d seoul_safety

# 컨테이너 중지
docker-compose down

# 볼륨까지 삭제 (DB 초기화)
docker-compose down -v
```
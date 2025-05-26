# 한국 기업 재무정보 분석 시스템

DART(전자공시시스템) API를 활용한 한국 상장기업의 재무정보 조회 및 분석 웹 애플리케이션입니다.

## 주요 기능

### 📊 재무정보 조회
- 한국 상장기업 검색 및 선택
- 실시간 DART API 연동으로 최신 재무데이터 제공
- 매출액, 영업이익, 당기순이익, 자산총계 등 주요 지표 표시

### 📈 시각화 분석
- **자산/부채/자본 구성**: 도넛 차트로 재무구조 시각화
- **매출액 3년 추이**: 라인 차트로 성장 추세 분석
- **영업이익/당기순이익 추이**: 수익성 변화 추적

### 🤖 AI 재무분석
- OpenAI GPT를 활용한 전문적인 재무분석 보고서 자동 생성
- 수익성, 안정성, 투자 관점의 종합적 분석
- 리스크 요인 및 투자 시사점 제공

### 💼 기업정보 관리
- 20,000+ 한국 기업 데이터베이스
- 상장/비상장 구분 및 필터링
- 기업코드, 주식코드 기반 정확한 매칭

## 기술 스택

- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, JavaScript
- **Charts**: Chart.js
- **Database**: SQLite
- **APIs**: 
  - DART Open API (금융감독원)
  - OpenAI GPT API
- **Styling**: Font Awesome, Custom CSS

## 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/korean-finance-analyzer.git
cd korean-finance-analyzer
```

### 2. 가상환경 설정
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정
`.env` 파일을 생성하고 다음 내용을 추가:
```
DART_API_KEY=your_dart_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

#### API 키 발급 방법:
- **DART API**: [DART 오픈API](https://opendart.fss.or.kr/) 회원가입 후 발급
- **OpenAI API**: [OpenAI Platform](https://platform.openai.com/) 계정 생성 후 발급

### 5. 애플리케이션 실행
```bash
python app.py
```

브라우저에서 `http://localhost:5000` 접속

## 사용법

1. **기업 검색**: 메인 페이지에서 기업명으로 검색
2. **기업 선택**: 검색 결과에서 원하는 기업 클릭
3. **재무정보 확인**: 
   - 상단 재무 요약 카드에서 주요 지표 확인
   - 탭 메뉴를 통해 상세 정보 탐색
4. **차트 분석**: "차트 분석" 탭에서 시각화된 데이터 확인
5. **AI 분석**: "AI 분석 보고서 생성" 버튼으로 전문 분석 리포트 생성

## 프로젝트 구조

```
finance2/
├── app.py                 # Flask 메인 애플리케이션
├── companies.db          # 기업 정보 데이터베이스
├── requirements.txt      # Python 패키지 의존성
├── .env                  # 환경변수 (git에서 제외)
├── templates/
│   ├── index.html        # 메인 페이지
│   └── company_detail.html # 기업 상세 페이지
└── static/              # 정적 파일 (CSS, JS, 이미지)
```

## 주요 API 엔드포인트

- `GET /` - 메인 페이지
- `GET /company/<corp_code>` - 기업 상세 페이지
- `GET /api/companies` - 기업 목록 조회
- `GET /api/financial/<corp_code>` - 재무정보 조회
- `GET /api/financial/<corp_code>/ai_report` - AI 분석 보고서

## 데이터 소스

- **기업 기본정보**: DART 고유번호 기반 기업정보
- **재무데이터**: DART API 단일회사 전체 재무제표
- **AI 분석**: OpenAI GPT-3.5-turbo 모델

## 라이선스

MIT License

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 문의

프로젝트에 대한 문의사항이나 버그 리포트는 Issues 탭을 이용해주세요.

---

**⚠️ 주의사항**: 
- DART API와 OpenAI API 키가 필요합니다
- API 사용량에 따른 비용이 발생할 수 있습니다
- 재무데이터는 DART 공시 기준이며, 투자 결정의 유일한 근거로 사용하지 마세요 
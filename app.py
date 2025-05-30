from flask import Flask, render_template, request, jsonify
import sqlite3
import json
import requests
from datetime import datetime
import re
import os
from dotenv import load_dotenv
from openai import OpenAI

# 환경 변수 로드
print("=== 환경 변수 로딩 시작 ===", flush=True)
print("현재 작업 디렉토리:", os.getcwd(), flush=True)
print("Python 실행 환경:", os.environ.get('PYTHON_VERSION', 'Unknown'), flush=True)

# 로컬 개발환경에서만 .env 파일 로드
if os.path.exists('.env'):
    load_dotenv(override=True)
    print("✅ .env 파일을 로드했습니다 (로컬 개발환경)", flush=True)
else:
    print("ℹ️ .env 파일이 없습니다. 시스템 환경 변수를 사용합니다 (Render 배포환경)", flush=True)

# 환경 변수 직접 확인
print("\n=== 중요 환경 변수 확인 ===", flush=True)

# 1. OpenAI API 키 관련 환경 변수들 확인
openai_keys_to_check = [
    'OPENAI_API_KEY',
    'OPENAPI_KEY', 
    'OPEN_AI_API_KEY',
    'OPENAI_KEY',
    'OPENAI_SECRET_KEY'
]

print("OpenAI 관련 환경 변수 검사:", flush=True)
found_openai_key = None
for key_name in openai_keys_to_check:
    value = os.environ.get(key_name)
    if value:
        print(f"  ✅ {key_name}: 발견됨 (길이: {len(value)}, 시작: {value[:15]}...)", flush=True)
        if not found_openai_key:  # 첫 번째로 발견된 키 사용
            found_openai_key = value
    else:
        print(f"  ❌ {key_name}: 없음", flush=True)

# 2. 모든 환경 변수 중 API/KEY 포함된 것들 확인
print("\n모든 API/KEY 관련 환경 변수:", flush=True)
api_env_vars = {k: v for k, v in os.environ.items() if any(keyword in k.upper() for keyword in ['API', 'KEY', 'SECRET', 'TOKEN'])}
for key, value in api_env_vars.items():
    if value:
        # 보안을 위해 값의 일부만 표시
        masked_value = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else f"{value[:6]}..."
        print(f"  {key}: {masked_value}", flush=True)
    else:
        print(f"  {key}: (빈 값)", flush=True)

print("=== 환경 변수 로딩 완료 ===\n", flush=True)

app = Flask(__name__)

# OpenAI API 설정 - 발견된 키 사용
OPENAI_API_KEY = found_openai_key or os.getenv('OPENAI_API_KEY')
print("=== OpenAI API 키 설정 ===", flush=True)
print("OPENAI_API_KEY 존재 여부:", OPENAI_API_KEY is not None, flush=True)
if OPENAI_API_KEY:
    print("OPENAI_API_KEY 길이:", len(OPENAI_API_KEY), flush=True)
    print("OPENAI_API_KEY 형식 확인:", flush=True)
    if OPENAI_API_KEY.startswith('sk-'):
        print("  ✅ 올바른 OpenAI API 키 형식 (sk-로 시작)", flush=True)
    elif OPENAI_API_KEY.startswith('sk-proj-'):
        print("  ✅ 올바른 OpenAI 프로젝트 API 키 형식 (sk-proj-로 시작)", flush=True)
    else:
        print("  ⚠️ 비정상적인 API 키 형식 (sk- 또는 sk-proj-로 시작하지 않음)", flush=True)
    print("OPENAI_API_KEY 시작 부분:", OPENAI_API_KEY[:15] + "..." if len(OPENAI_API_KEY) > 15 else OPENAI_API_KEY, flush=True)
else:
    print("❌ OPENAI_API_KEY를 찾을 수 없습니다!", flush=True)
    print("Render 대시보드에서 Environment Variables 설정을 확인해주세요.", flush=True)
print("========================\n", flush=True)

# OpenAI 클라이언트 초기화
print("=== OpenAI 클라이언트 초기화 ===", flush=True)

# OpenAI 라이브러리 버전 확인
try:
    import openai
    openai_version = getattr(openai, '__version__', 'Unknown')
    print(f"📦 OpenAI 라이브러리 버전: {openai_version}", flush=True)
except Exception as ve:
    print(f"⚠️ OpenAI 라이브러리 버전 확인 실패: {str(ve)}", flush=True)

openai_client = None

if OPENAI_API_KEY and len(OPENAI_API_KEY.strip()) > 0:
    try:
        print(f"🔄 OpenAI 클라이언트 초기화 시도 중...", flush=True)
        print(f"   API 키 길이: {len(OPENAI_API_KEY)}", flush=True)
        print(f"   API 키 형식: {OPENAI_API_KEY[:20]}...", flush=True)
        
        # OpenAI 클라이언트 생성
        try:
            # 기본적인 방식으로 클라이언트 생성 (최대 호환성)
            openai_client = OpenAI(api_key=OPENAI_API_KEY.strip())
            print("✅ OpenAI 클라이언트 객체 생성 성공", flush=True)
        except TypeError as te:
            # 구버전 호환성을 위한 대체 방식
            print(f"⚠️ 기본 방식 실패, 호환성 모드로 재시도: {str(te)}", flush=True)
            try:
                import openai
                openai.api_key = OPENAI_API_KEY.strip()
                # 구버전 방식으로 설정
                print("✅ OpenAI 클라이언트 호환성 모드로 설정 완료", flush=True)
                # 새로운 방식으로 다시 시도
                openai_client = OpenAI(api_key=OPENAI_API_KEY.strip())
                print("✅ OpenAI 클라이언트 객체 생성 성공 (호환성 모드)", flush=True)
            except Exception as ce:
                print(f"❌ 호환성 모드도 실패: {str(ce)}", flush=True)
                raise ce
        
        # API 연결 테스트 (간단한 모델 목록 조회)
        try:
            print("🔄 OpenAI API 연결 테스트 중...", flush=True)
            models_response = openai_client.models.list()
            if models_response and hasattr(models_response, 'data'):
                available_models = [model.id for model in models_response.data[:3]]  # 처음 3개만
                print(f"✅ OpenAI API 연결 테스트 성공! 사용 가능한 모델: {available_models}", flush=True)
            else:
                print("✅ OpenAI API 연결 성공 (모델 목록 확인 불가)", flush=True)
        except Exception as test_e:
            print(f"⚠️ OpenAI API 연결 테스트 실패: {str(test_e)}", flush=True)
            print("   클라이언트는 생성되었지만 API 호출에 문제가 있을 수 있습니다.", flush=True)
            # API 테스트 실패해도 클라이언트는 유지 (실제 사용 시 재시도 가능)
            
    except Exception as e:
        print(f"❌ OpenAI 클라이언트 초기화 실패: {str(e)}", flush=True)
        print(f"   오류 타입: {type(e).__name__}", flush=True)
        openai_client = None
        
        # 일반적인 오류 원인 안내
        if "api_key" in str(e).lower():
            print("   💡 API 키 관련 오류입니다. 키 형식을 확인해주세요.", flush=True)
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            print("   💡 네트워크 연결 오류입니다. 인터넷 연결을 확인해주세요.", flush=True)
        else:
            print("   💡 예상치 못한 오류입니다. OpenAI 서비스 상태를 확인해주세요.", flush=True)
            
else:
    print("❌ OpenAI API 키가 없거나 비어있어 클라이언트를 초기화하지 않습니다.", flush=True)
    print("   Render 환경 변수 'OPENAI_API_KEY'를 확인해주세요.", flush=True)

# 최종 상태 출력
if openai_client:
    print("🎉 OpenAI 클라이언트 준비 완료! AI 분석 보고서 기능이 활성화됩니다.", flush=True)
else:
    print("💔 OpenAI 클라이언트 초기화 실패. AI 분석 보고서 기능이 비활성화됩니다.", flush=True)

print("=== OpenAI 클라이언트 초기화 완료 ===\n", flush=True)

# DART Open API 설정
DART_API_KEY = os.getenv('DART_API_KEY')
print("DART_API_KEY 존재 여부:", DART_API_KEY is not None, flush=True)
print("DART_API_KEY 길이:", len(DART_API_KEY) if DART_API_KEY else 0, flush=True)
if not DART_API_KEY:
    print("Warning: DART_API_KEY not found in environment variables", flush=True)
DART_API_BASE_URL = "https://opendart.fss.or.kr/api"

# API 응답 상태 코드
DART_STATUS_CODES = {
    '000': '정상',
    '010': '등록되지 않은 키입니다.',
    '011': '사용할 수 없는 키입니다.',
    '012': '접근할 수 없는 IP입니다.',
    '013': '조회된 데이터가 없습니다.',
    '014': '파일이 존재하지 않습니다.',
    '020': '요청 제한을 초과하였습니다.',
    '100': '필드의 부적절한 값입니다.',
    '800': '시스템 점검 중입니다.',
    '900': '정의되지 않은 오류가 발생하였습니다.'
}

def get_db_connection():
    """데이터베이스 연결"""
    db_path = os.path.join(os.getenv('DATA_PATH', ''), 'companies.db')
    if not os.path.exists(db_path):
        # 데이터베이스 파일이 없으면 현재 디렉토리의 파일을 복사
        import shutil
        current_db = 'companies.db'
        if os.path.exists(current_db):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            shutil.copy2(current_db, db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def clean_number(value):
    """숫자 데이터 정리 (콤마 제거 및 float 변환)"""
    if not value:
        return 0.0
    try:
        # 콤마 제거 후 float 변환
        cleaned = str(value).replace(',', '').replace(' ', '')
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0

def format_amount(amount):
    """금액을 조원/억원 단위로 포맷"""
    try:
        num = float(amount)
        if num >= 1000000000000:  # 1조 이상
            return f"{num/1000000000000:.1f}조원"
        elif num >= 100000000:  # 1억 이상
            return f"{num/100000000:.0f}억원"
        else:
            return f"{num:,.0f}원"
    except:
        return str(amount)

def get_financial_data(corp_code, bsns_year="2023", reprt_code="11011"):
    """DART API에서 재무정보 가져오기"""
    if not DART_API_KEY:
        print("DART API 키가 없습니다!", flush=True)
        return {
            'status': 'error',
            'message': 'DART API 키가 설정되지 않았습니다.',
            'data': []
        }

    try:
        # DART API 엔드포인트 직접 호출
        url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
        params = {
            'crtfc_key': DART_API_KEY,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': reprt_code
        }
        
        print("\n=== DART API 요청 정보 ===", flush=True)
        print(f"URL: {url}", flush=True)
        print(f"API Key: {DART_API_KEY}", flush=True)
        print(f"기업코드: {corp_code}", flush=True)
        print(f"사업연도: {bsns_year}", flush=True)
        print(f"보고서 코드: {reprt_code}", flush=True)
        
        # 실제 요청 URL 출력 (디버깅용)
        full_url = f"{url}?crtfc_key={DART_API_KEY}&corp_code={corp_code}&bsns_year={bsns_year}&reprt_code={reprt_code}"
        print(f"전체 URL: {full_url}", flush=True)
        print("========================\n", flush=True)
        
        response = requests.get(url, params=params, timeout=10)
        print(f"응답 상태 코드: {response.status_code}", flush=True)
        print(f"실제 요청 URL: {response.url}", flush=True)
        
        response.raise_for_status()
        data = response.json()
        
        print(f"API 응답: {data.get('status')} - {DART_STATUS_CODES.get(data.get('status'), '알 수 없는 상태')}", flush=True)
        
        status = data.get('status')
        if status == '000':
            # 연결재무제표와 개별재무제표 분리
            cfs_data = [item for item in data.get('list', []) if item.get('fs_div') == 'CFS']
            ofs_data = [item for item in data.get('list', []) if item.get('fs_div') == 'OFS']
            
            # 재무상태표와 손익계산서 분리
            financial_data = {
                'cfs': {
                    'bs': [item for item in cfs_data if item.get('sj_div') == 'BS'],
                    'is': [item for item in cfs_data if item.get('sj_div') == 'IS']
                },
                'ofs': {
                    'bs': [item for item in ofs_data if item.get('sj_div') == 'BS'],
                    'is': [item for item in ofs_data if item.get('sj_div') == 'IS']
                }
            }
            
            return {
                'status': 'success',
                'message': DART_STATUS_CODES.get(status, '알 수 없는 상태'),
                'data': financial_data
            }
        else:
            error_message = DART_STATUS_CODES.get(status, '알 수 없는 오류')
            print(f"DART API 오류 ({status}): {error_message}", flush=True)
            return {
                'status': 'error',
                'message': f"DART API 오류: {error_message}",
                'data': []
            }
            
    except requests.exceptions.Timeout:
        print("DART API 요청 시간 초과", flush=True)
        return {
            'status': 'error',
            'message': 'DART API 요청 시간이 초과되었습니다.',
            'data': []
        }
    except requests.exceptions.RequestException as e:
        print(f"DART API 요청 오류: {e}", flush=True)
        return {
            'status': 'error',
            'message': 'DART API 요청 중 오류가 발생했습니다.',
            'data': []
        }
    except Exception as e:
        print(f"재무정보 조회 오류: {e}", flush=True)
        return {
            'status': 'error',
            'message': '재무정보를 처리하는 중 오류가 발생했습니다.',
            'data': []
        }

def calculate_financial_ratios(financial_data):
    """재무비율 계산"""
    ratios = {}
    
    try:
        # 연결재무제표 데이터 사용
        bs_data = financial_data['cfs']['bs']
        is_data = financial_data['cfs']['is']
        
        # 주요 계정 찾기
        def find_account(data, account_name):
            for item in data:
                if item.get('account_nm') == account_name:
                    return {
                        'current': clean_number(item.get('thstrm_amount', 0)),
                        'previous': clean_number(item.get('frmtrm_amount', 0)),
                        'previous2': clean_number(item.get('bfefrmtrm_amount', 0))
                    }
            return {'current': 0, 'previous': 0, 'previous2': 0}
        
        # 재무상태표 계정
        assets = find_account(bs_data, '자산총계')
        liabilities = find_account(bs_data, '부채총계')
        equity = find_account(bs_data, '자본총계')
        current_assets = find_account(bs_data, '유동자산')
        current_liabilities = find_account(bs_data, '유동부채')
        
        # 손익계산서 계정
        revenue = find_account(is_data, '매출액')
        operating_profit = find_account(is_data, '영업이익')
        net_income = find_account(is_data, '당기순이익')
        
        # 수익성 비율 계산
        if revenue['current'] > 0:
            ratios['operating_margin'] = round((operating_profit['current'] / revenue['current']) * 100, 1)
            ratios['net_margin'] = round((net_income['current'] / revenue['current']) * 100, 1)
        
        # 안정성 비율 계산
        if equity['current'] > 0:
            ratios['debt_ratio'] = round((liabilities['current'] / equity['current']) * 100, 1)
            ratios['roe'] = round((net_income['current'] / equity['current']) * 100, 1)
        
        if assets['current'] > 0:
            ratios['roa'] = round((net_income['current'] / assets['current']) * 100, 1)
            ratios['equity_ratio'] = round((equity['current'] / assets['current']) * 100, 1)
        
        if current_liabilities['current'] > 0:
            ratios['current_ratio'] = round((current_assets['current'] / current_liabilities['current']) * 100, 1)
        
        # 기본 수치 저장 (포맷된 형태)
        ratios['revenue_formatted'] = format_amount(revenue['current'])
        ratios['operating_profit_formatted'] = format_amount(operating_profit['current'])
        ratios['net_income_formatted'] = format_amount(net_income['current'])
        ratios['total_assets_formatted'] = format_amount(assets['current'])
        ratios['total_liabilities_formatted'] = format_amount(liabilities['current'])
        ratios['total_equity_formatted'] = format_amount(equity['current'])
            
    except Exception as e:
        print(f"재무비율 계산 오류: {e}", flush=True)
    
    return ratios

def get_chart_data(financial_data):
    """차트용 데이터 추출"""
    chart_data = {}
    
    try:
        # 연결재무제표 데이터 사용
        bs_data = financial_data['cfs']['bs']
        is_data = financial_data['cfs']['is']
        
        def find_account(data, account_name):
            for item in data:
                if item.get('account_nm') == account_name:
                    return {
                        'current': clean_number(item.get('thstrm_amount', 0)),
                        'previous': clean_number(item.get('frmtrm_amount', 0)),
                        'previous2': clean_number(item.get('bfefrmtrm_amount', 0))
                    }
            return {'current': 0, 'previous': 0, 'previous2': 0}
        
        # 재무상태표 데이터 (조원 단위)
        assets = find_account(bs_data, '자산총계')
        liabilities = find_account(bs_data, '부채총계')
        equity = find_account(bs_data, '자본총계')
        
        chart_data['balance'] = {
            'labels': ['자산총계', '부채총계', '자본총계'],
            'data': [
                round(assets['current'] / 1000000000000, 1),
                round(liabilities['current'] / 1000000000000, 1),
                round(equity['current'] / 1000000000000, 1)
            ]
        }
        
        # 매출액 추이 (조원 단위)
        revenue = find_account(is_data, '매출액')
        chart_data['revenue_trend'] = {
            'labels': ['전전기', '전기', '당기'],
            'data': [
                round(revenue['previous2'] / 1000000000000, 1),
                round(revenue['previous'] / 1000000000000, 1),
                round(revenue['current'] / 1000000000000, 1)
            ]
        }
        
        # 이익 추이 (조원 단위)
        operating_profit = find_account(is_data, '영업이익')
        net_income = find_account(is_data, '당기순이익')
        
        chart_data['profit_trend'] = {
            'labels': ['전전기', '전기', '당기'],
            'operating_profit': [
                round(operating_profit['previous2'] / 1000000000000, 1),
                round(operating_profit['previous'] / 1000000000000, 1),
                round(operating_profit['current'] / 1000000000000, 1)
            ],
            'net_income': [
                round(net_income['previous2'] / 1000000000000, 1),
                round(net_income['previous'] / 1000000000000, 1),
                round(net_income['current'] / 1000000000000, 1)
            ]
        }
        
    except Exception as e:
        print(f"차트 데이터 생성 오류: {e}", flush=True)
    
    return chart_data

def get_enhanced_company_info(corp_code):
    """기업 정보를 상세히 조회하고 분석용 데이터를 준비"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM companies WHERE corp_code = ?', (corp_code,))
        company = cursor.fetchone()
        conn.close()
        
        if not company:
            return None
            
        company_dict = dict(company)
        
        # 기업 규모 분류 (자본금 기준)
        capital = clean_number(company_dict.get('capital', 0))
        if capital >= 50000000000:  # 500억 이상
            company_size = "대기업"
        elif capital >= 10000000000:  # 100억 이상
            company_size = "중견기업"
        elif capital >= 1000000000:  # 10억 이상
            company_size = "중소기업"
        else:
            company_size = "소기업"
            
        # 상장 여부 확인
        listing_status = "상장기업" if company_dict.get('stock_code') and company_dict.get('stock_code').strip() else "비상장기업"
        
        # 업종 정보 정리
        industry = company_dict.get('industry', '정보 없음')
        if industry == '정보 없음' or not industry:
            # 회사명에서 업종 추정 시도
            corp_name = company_dict.get('corp_name', '')
            if any(keyword in corp_name for keyword in ['전자', '반도체', 'IT', '소프트웨어']):
                industry = "IT/전자"
            elif any(keyword in corp_name for keyword in ['건설', '건축', '토목']):
                industry = "건설업"
            elif any(keyword in corp_name for keyword in ['금융', '은행', '증권', '보험']):
                industry = "금융업"
            elif any(keyword in corp_name for keyword in ['제약', '바이오', '의료']):
                industry = "제약/바이오"
            elif any(keyword in corp_name for keyword in ['화학', '석유', '정유']):
                industry = "화학/석유"
            else:
                industry = "기타 업종"
        
        # 설립연도 계산
        est_date = company_dict.get('est_date', '')
        company_age = "정보 없음"
        if est_date:
            try:
                from datetime import datetime
                if len(est_date) >= 4:
                    est_year = int(est_date[:4])
                    current_year = datetime.now().year
                    company_age = f"{current_year - est_year}년"
            except:
                pass
        
        # 강화된 기업 정보
        enhanced_info = {
            **company_dict,
            'company_size': company_size,
            'listing_status': listing_status,
            'industry_classified': industry,
            'company_age': company_age,
            'capital_formatted': format_amount(capital) if capital > 0 else "정보 없음"
        }
        
        return enhanced_info
        
    except Exception as e:
        print(f"기업 정보 조회 오류: {e}", flush=True)
        return None

def generate_financial_report(company_info, financial_data, ratios):
    """AI를 사용하여 재무 보고서 생성"""
    try:
        if not openai_client:
            print("OpenAI 클라이언트가 초기화되지 않았습니다.", flush=True)
            return {
                'status': 'error',
                'message': 'OpenAI API 키가 설정되지 않았거나 유효하지 않습니다.'
            }

        # 업종별 특성 분석을 위한 추가 정보
        industry_context = ""
        industry = company_info.get('industry_classified', '기타')
        
        if "IT" in industry or "전자" in industry:
            industry_context = "IT/전자 업종은 기술 혁신과 R&D 투자가 중요하며, 빠른 시장 변화에 대응력이 핵심입니다."
        elif "건설" in industry:
            industry_context = "건설업은 경기 민감도가 높고, 프로젝트 기반 매출로 인한 변동성이 큰 특징이 있습니다."
        elif "금융" in industry:
            industry_context = "금융업은 금리 변동과 경제 상황에 민감하며, 자본 적정성과 리스크 관리가 중요합니다."
        elif "제약" in industry or "바이오" in industry:
            industry_context = "제약/바이오 업종은 높은 R&D 비용과 긴 개발 기간, 규제 리스크가 특징입니다."
        elif "화학" in industry or "석유" in industry:
            industry_context = "화학/석유 업종은 원자재 가격 변동과 환경 규제에 민감한 특성을 가집니다."
        else:
            industry_context = "해당 업종의 특성을 고려한 분석이 필요합니다."

        # 강화된 프롬프트 구성
        prompt = f"""
=== 기업 기본 정보 ===
• 회사명: {company_info['corp_name']}
• 기업코드: {company_info['corp_code']}
• 업종: {company_info.get('industry_classified', '정보 없음')}
• 기업 규모: {company_info.get('company_size', '정보 없음')}
• 상장 여부: {company_info.get('listing_status', '정보 없음')}
• 설립 연수: {company_info.get('company_age', '정보 없음')}
• 자본금: {company_info.get('capital_formatted', '정보 없음')}
{f"• 주식코드: {company_info['stock_code']}" if company_info.get('stock_code') else ""}

=== 업종 특성 ===
{industry_context}

=== 주요 재무 지표 (최근 연도 기준) ===
• 매출액: {ratios.get('revenue_formatted', '정보 없음')}
• 영업이익: {ratios.get('operating_profit_formatted', '정보 없음')}
• 당기순이익: {ratios.get('net_income_formatted', '정보 없음')}
• 자산총계: {ratios.get('total_assets_formatted', '정보 없음')}
• 부채총계: {ratios.get('total_liabilities_formatted', '정보 없음')}
• 자본총계: {ratios.get('total_equity_formatted', '정보 없음')}

=== 재무비율 분석 ===
• 영업이익률: {ratios.get('operating_margin', '정보 없음')}%
• 순이익률: {ratios.get('net_margin', '정보 없음')}%
• ROE(자기자본이익률): {ratios.get('roe', '정보 없음')}%
• ROA(총자산이익률): {ratios.get('roa', '정보 없음')}%
• 부채비율: {ratios.get('debt_ratio', '정보 없음')}%
• 자기자본비율: {ratios.get('equity_ratio', '정보 없음')}%
• 유동비율: {ratios.get('current_ratio', '정보 없음')}%

위 정보를 바탕으로 다음 내용을 포함하는 전문적인 재무 분석 보고서를 작성해주세요:

1. **기업 개요 및 사업 특성**
   - 기업의 주요 사업 영역과 업종 내 위치
   - 기업 규모와 시장에서의 역할

2. **재무 상태 종합 평가**
   - 매출 규모와 수익성 수준 평가
   - 재무 안정성 및 건전성 분석

3. **업종 대비 경쟁력 분석**
   - 해당 업종의 일반적 특성 대비 이 기업의 강점/약점
   - 업종별 주요 관심 지표 중심 분석

4. **투자 관점에서의 평가**
   - 투자 매력도와 주요 투자 포인트
   - 기업 가치 평가 관련 시사점

5. **리스크 요인 및 주의사항**
   - 업종별 특성을 고려한 주요 리스크
   - 재무 지표상 나타나는 잠재적 위험 요소

보고서는 구체적인 수치를 인용하며 객관적이고 전문적인 톤으로 작성해주세요.
"""

        print("\n=== OpenAI SDK 요청 정보 ===", flush=True)
        print(f"클라이언트 상태: {'초기화됨' if openai_client else '초기화 안됨'}", flush=True)
        print(f"모델: gpt-3.5-turbo", flush=True)
        print("========================\n", flush=True)

        # OpenAI SDK 사용
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # 더 안정적인 모델 사용
            messages=[
                {"role": "system", "content": "당신은 전문 재무분석가입니다. 주어진 재무정보를 바탕으로 객관적이고 통찰력 있는 분석 보고서를 작성해주세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            timeout=60  # 타임아웃을 60초로 증가
        )
        
        print("OpenAI API 호출 성공", flush=True)
        
        report = response.choices[0].message.content
        return {
            'status': 'success',
            'report': report
        }
            
    except Exception as e:
        print(f"AI 보고서 생성 오류: {e}", flush=True)
        return {
            'status': 'error',
            'message': f'AI 보고서 생성 중 오류가 발생했습니다: {str(e)}'
        }

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/company/<corp_code>')
def company_detail(corp_code):
    """회사 상세 페이지"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 회사 기본 정보 조회
    cursor.execute('SELECT * FROM companies WHERE corp_code = ?', (corp_code,))
    company = cursor.fetchone()
    conn.close()
    
    if not company:
        return "회사를 찾을 수 없습니다.", 404
    
    # 주식코드가 없는 회사는 재무정보 접근 불가
    if not company['stock_code'] or not company['stock_code'].strip():
        return render_template('company_detail.html', 
                             company=dict(company), 
                             is_unlisted=True)
    
    return render_template('company_detail.html', 
                         company=dict(company), 
                         is_unlisted=False)

@app.route('/api/financial/<corp_code>')
def get_company_financial(corp_code):
    """회사 재무정보 API"""
    # 주식코드 확인
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM companies WHERE corp_code = ?', (corp_code,))
    company = cursor.fetchone()
    conn.close()
    
    if not company or not company['stock_code'] or not company['stock_code'].strip():
        return jsonify({'error': '비상장회사는 재무정보를 제공하지 않습니다.'}), 400
    
    year = request.args.get('year', '2023')
    report_type = request.args.get('report_type', '11011')  # 사업보고서
    
    # DART API에서 재무데이터 조회
    financial_result = get_financial_data(corp_code, year, report_type)
    
    if financial_result['status'] == 'error':
        return jsonify({
            'error': financial_result['message'],
            'financial_ratios': {},
            'chart_data': {},
            'table_data': [],
            'raw_data': [],
            'ai_report': {
                'status': 'error',
                'message': '재무정보를 불러올 수 없어 AI 분석을 수행할 수 없습니다.'
            }
        })

    financial_data = financial_result['data']
    
    # 재무비율 계산
    ratios = calculate_financial_ratios(financial_data)
    
    # 차트용 데이터 생성
    chart_data = get_chart_data(financial_data)
    
    # 재무제표 테이블용 데이터
    table_data = []
    key_accounts = ['매출액', '영업이익', '당기순이익', '자산총계', '부채총계', '자본총계']
    
    # 재무상태표와 손익계산서 모두에서 찾기
    all_items = financial_data['cfs']['bs'] + financial_data['cfs']['is']
    
    for account in key_accounts:
        for item in all_items:
            if item.get('account_nm') == account:
                table_data.append({
                    'account_nm': item.get('account_nm'),
                    'thstrm_amount': format_amount(clean_number(item.get('thstrm_amount', 0))),
                    'frmtrm_amount': format_amount(clean_number(item.get('frmtrm_amount', 0))),
                    'bfefrmtrm_amount': format_amount(clean_number(item.get('bfefrmtrm_amount', 0)))
                })
                break
    
    # AI 보고서 상태 확인
    ai_report_status = {
        'status': 'disabled',
        'message': 'AI 분석 보고서 기능이 현재 비활성화되어 있습니다. OpenAI API 키를 설정해주세요.'
    }
    
    if openai_client:
        ai_report_status = {
            'status': 'enabled',
            'message': 'AI 분석 보고서를 사용할 수 있습니다.'
        }
    
    return jsonify({
        'financial_ratios': ratios,
        'chart_data': chart_data,
        'table_data': table_data,
        'raw_data': financial_data['cfs']['bs'][:10],  # 상위 10개만
        'ai_report': ai_report_status
    })

@app.route('/api/financial/<corp_code>/ai_report')
def get_ai_report(corp_code):
    """AI 분석 보고서 생성 API"""
    try:
        # 강화된 회사 정보 조회
        print(f"🔍 기업 정보 조회 시작: {corp_code}", flush=True)
        enhanced_company_info = get_enhanced_company_info(corp_code)
        
        if not enhanced_company_info:
            return jsonify({
                'status': 'error',
                'message': '회사를 찾을 수 없습니다.'
            }), 404
        
        print(f"✅ 기업 정보 조회 완료: {enhanced_company_info['corp_name']} ({enhanced_company_info.get('industry_classified', '업종 미분류')})", flush=True)
        
        # 비상장회사 체크
        if not enhanced_company_info['stock_code'] or not enhanced_company_info['stock_code'].strip():
            return jsonify({
                'status': 'error',
                'message': '비상장회사는 AI 분석 보고서를 제공하지 않습니다.'
            }), 400
        
        year = request.args.get('year', '2023')
        report_type = request.args.get('report_type', '11011')
        
        print(f"📊 재무데이터 조회 시작: {year}년 {report_type} 보고서", flush=True)
        
        # 재무데이터 조회
        financial_result = get_financial_data(corp_code, year, report_type)
        if financial_result['status'] == 'error':
            return jsonify({
                'status': 'error',
                'message': f'재무정보 조회 실패: {financial_result["message"]}'
            }), 400
            
        financial_data = financial_result['data']
        ratios = calculate_financial_ratios(financial_data)
        
        print(f"💰 재무비율 계산 완료: 매출액 {ratios.get('revenue_formatted', 'N/A')}, 영업이익률 {ratios.get('operating_margin', 'N/A')}%", flush=True)
        
        # 강화된 기업 정보로 AI 보고서 생성
        print(f"🤖 AI 분석 보고서 생성 시작...", flush=True)
        ai_report = generate_financial_report(enhanced_company_info, financial_data, ratios)
        
        if ai_report['status'] == 'success':
            print(f"✅ AI 분석 보고서 생성 완료 (길이: {len(ai_report.get('report', ''))}자)", flush=True)
        else:
            print(f"❌ AI 분석 보고서 생성 실패: {ai_report.get('message', 'Unknown error')}", flush=True)
        
        return jsonify(ai_report)
        
    except Exception as e:
        print(f"AI 보고서 API 오류: {e}", flush=True)
        return jsonify({
            'status': 'error',
            'message': 'AI 보고서 생성 중 서버 오류가 발생했습니다.'
        }), 500

@app.route('/api/companies')
def get_companies():
    """회사 목록 API"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 검색 조건에 따라 전체 개수 먼저 조회
    if search:
        # 전체 검색 결과 수
        count_query = '''
        SELECT COUNT(*) FROM companies 
        WHERE corp_name LIKE ? OR corp_code LIKE ? OR stock_code LIKE ?
        '''
        search_term = f'%{search}%'
        cursor.execute(count_query, (search_term, search_term, search_term))
        total = cursor.fetchone()[0]
        
        # 페이지네이션된 검색 결과
        query = '''
        SELECT * FROM companies 
        WHERE corp_name LIKE ? OR corp_code LIKE ? OR stock_code LIKE ?
        ORDER BY corp_name
        LIMIT ? OFFSET ?
        '''
        cursor.execute(query, (search_term, search_term, search_term, per_page, (page-1)*per_page))
    else:
        # 전체 회사 수
        cursor.execute('SELECT COUNT(*) FROM companies')
        total = cursor.fetchone()[0]
        
        # 페이지네이션된 전체 결과
        query = 'SELECT * FROM companies ORDER BY corp_name LIMIT ? OFFSET ?'
        cursor.execute(query, (per_page, (page-1)*per_page))
    
    companies = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'companies': companies,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/api/company/<corp_code>')
def get_company(corp_code):
    """특정 회사 정보 API"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM companies WHERE corp_code = ?', (corp_code,))
    company = cursor.fetchone()
    
    conn.close()
    
    if company:
        return jsonify(dict(company))
    else:
        return jsonify({'error': '회사를 찾을 수 없습니다'}), 404

@app.route('/api/stats')
def get_stats():
    """통계 정보 API"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 전체 회사 수
    cursor.execute('SELECT COUNT(*) FROM companies')
    total_companies = cursor.fetchone()[0]
    
    # 실제 상장회사 수 (주식코드가 있는 회사)
    cursor.execute("SELECT COUNT(*) FROM companies WHERE LENGTH(TRIM(COALESCE(stock_code, ''))) > 0")
    listed_companies = cursor.fetchone()[0]
    
    # 비상장회사 수
    unlisted_companies = total_companies - listed_companies
    
    # 최근 수정된 회사들
    cursor.execute('''
    SELECT corp_name, modify_date 
    FROM companies 
    WHERE modify_date IS NOT NULL 
    ORDER BY modify_date DESC 
    LIMIT 10
    ''')
    recent_updates = [dict(row) for row in cursor.fetchall()]
    
    # 주요 상장회사 샘플
    cursor.execute('''
    SELECT corp_name, stock_code 
    FROM companies 
    WHERE LENGTH(TRIM(COALESCE(stock_code, ''))) > 0
    ORDER BY corp_name
    LIMIT 10
    ''')
    sample_listed = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'total_companies': total_companies,
        'listed_companies': listed_companies,
        'unlisted_companies': unlisted_companies,
        'recent_updates': recent_updates,
        'sample_listed': sample_listed
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 
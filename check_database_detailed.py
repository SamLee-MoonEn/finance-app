import sqlite3

def check_database_detailed():
    """SQLite 데이터베이스 내용을 더 자세히 확인"""
    conn = sqlite3.connect('companies.db')
    cursor = conn.cursor()
    
    # 전체 회사 수 확인
    cursor.execute('SELECT COUNT(*) FROM companies')
    total_count = cursor.fetchone()[0]
    print(f"전체 회사 수: {total_count:,}")
    
    # 주식코드 상태별 확인
    print("\n주식코드 상태별 분석:")
    
    # NULL 값
    cursor.execute('SELECT COUNT(*) FROM companies WHERE stock_code IS NULL')
    null_count = cursor.fetchone()[0]
    print(f"주식코드가 NULL인 회사: {null_count:,}")
    
    # 빈 문자열
    cursor.execute('SELECT COUNT(*) FROM companies WHERE stock_code = ""')
    empty_count = cursor.fetchone()[0]
    print(f"주식코드가 빈 문자열인 회사: {empty_count:,}")
    
    # 공백만 있는 경우
    cursor.execute("SELECT COUNT(*) FROM companies WHERE TRIM(stock_code) = ''")
    whitespace_count = cursor.fetchone()[0]
    print(f"주식코드가 공백만 있는 회사: {whitespace_count:,}")
    
    # 실제 주식코드가 있는 회사 (공백 제거 후 길이가 0보다 큰 경우)
    cursor.execute("SELECT COUNT(*) FROM companies WHERE LENGTH(TRIM(COALESCE(stock_code, ''))) > 0")
    real_stock_count = cursor.fetchone()[0]
    print(f"실제 주식코드가 있는 회사: {real_stock_count:,}")
    
    # 실제 주식코드가 있는 회사 샘플 확인
    print("\n실제 주식코드가 있는 회사 샘플:")
    cursor.execute('''
    SELECT corp_name, corp_code, stock_code, modify_date 
    FROM companies 
    WHERE LENGTH(TRIM(COALESCE(stock_code, ''))) > 0
    ORDER BY corp_name
    LIMIT 20
    ''')
    
    real_listed_companies = cursor.fetchall()
    if real_listed_companies:
        for row in real_listed_companies:
            print(f"- {row[0]} (코드: {row[1]}, 주식: '{row[2]}', 수정일: {row[3]})")
    else:
        print("실제 주식코드가 있는 회사가 없습니다.")
    
    # 주식코드 길이별 분포 확인
    print("\n주식코드 길이별 분포:")
    for length in range(1, 8):
        cursor.execute(f"SELECT COUNT(*) FROM companies WHERE LENGTH(TRIM(COALESCE(stock_code, ''))) = {length}")
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"길이 {length}: {count:,}개")
    
    # 특정 패턴 확인 (6자리 숫자 등)
    cursor.execute("SELECT COUNT(*) FROM companies WHERE stock_code REGEXP '^[0-9]{6}$'")
    try:
        six_digit_count = cursor.fetchone()[0]
        print(f"6자리 숫자 패턴: {six_digit_count:,}개")
    except:
        print("REGEXP 함수를 지원하지 않습니다.")
    
    conn.close()

if __name__ == "__main__":
    check_database_detailed() 
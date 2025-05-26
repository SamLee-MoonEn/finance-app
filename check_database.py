import sqlite3

def check_database():
    """SQLite 데이터베이스 내용 확인"""
    conn = sqlite3.connect('companies.db')
    cursor = conn.cursor()
    
    # 전체 회사 수 확인
    cursor.execute('SELECT COUNT(*) FROM companies')
    total_count = cursor.fetchone()[0]
    print(f"전체 회사 수: {total_count:,}")
    
    # 주식코드가 있는 회사 수 확인
    cursor.execute('SELECT COUNT(*) FROM companies WHERE stock_code IS NOT NULL AND stock_code != ""')
    stock_count = cursor.fetchone()[0]
    print(f"주식코드가 있는 회사 수: {stock_count:,}")
    
    # 테이블 구조 확인
    cursor.execute('PRAGMA table_info(companies)')
    columns = cursor.fetchall()
    print("\n테이블 구조:")
    for col in columns:
        print(f"- {col[1]} ({col[2]})")
    
    # 샘플 데이터 (주식코드가 있는 회사들)
    print("\n주식코드가 있는 회사 샘플:")
    cursor.execute('''
    SELECT corp_name, corp_code, stock_code, modify_date 
    FROM companies 
    WHERE stock_code IS NOT NULL AND stock_code != ""
    ORDER BY corp_name
    LIMIT 10
    ''')
    
    for row in cursor.fetchall():
        print(f"- {row[0]} (코드: {row[1]}, 주식: {row[2]}, 수정일: {row[3]})")
    
    # 대기업 검색 (삼성, LG, 현대 등)
    print("\n주요 대기업:")
    major_companies = ['삼성', 'LG', '현대', 'SK', '롯데', '포스코', 'KT', '신한', '한국']
    for company in major_companies:
        cursor.execute('''
        SELECT corp_name, corp_code, stock_code 
        FROM companies 
        WHERE corp_name LIKE ? AND stock_code IS NOT NULL AND stock_code != ""
        LIMIT 3
        ''', (f'%{company}%',))
        
        results = cursor.fetchall()
        if results:
            print(f"\n{company} 관련 회사:")
            for row in results:
                print(f"  - {row[0]} (주식코드: {row[2]})")
    
    conn.close()

if __name__ == "__main__":
    check_database() 
import sqlite3

# board 폴더 안의 boardgame.db 파일에 접속
conn = sqlite3.connect("boardgame.db")
cur = conn.cursor()

# 1) 기존 Role_Request 테이블이 있으면 먼저 삭제
cur.execute("DROP TABLE IF EXISTS Role_Request")

# 2) 올바른 구조로 다시 생성
cur.execute("""
CREATE TABLE Role_Request (
    req_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    from_role TEXT NOT NULL,
    to_role TEXT NOT NULL,
    status TEXT DEFAULT 'Pending'
);
""")

conn.commit()
conn.close()

print("Role_Request 테이블 재생성 완료!")

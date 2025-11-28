import sqlite3

# ================================
# 회원가입
# ================================
def sign_up():
    con = sqlite3.connect("boardgame.db")
    cur = con.cursor()

    print("\n=== 회원가입 ===")
    username = input("새 ID 입력: ")
    password = input("새 비밀번호 입력: ")
    location = input("사는 지역(선택): ")

    cur.execute("SELECT username FROM User WHERE username=?", (username,))
    if cur.fetchone():
        print("❌ 이미 존재하는 ID입니다.")
        return

    cur.execute("""
        INSERT INTO User (username, password_hash, location_info, role)
        VALUES (?, ?, ?, 'User')
    """, (username, password, location))

    con.commit()
    con.close()
    print("✅ 회원가입 완료!")


# ================================
# 로그인
# ================================
def login():
    con = sqlite3.connect("boardgame.db")
    cur = con.cursor()

    username = input("ID: ")
    pw = input("Password: ")

    cur.execute("""
        SELECT user_id, role FROM User
        WHERE username=? AND password_hash=?
    """, (username, pw))
    row = cur.fetchone()

    if not row:
        print("❌ 로그인 실패")
        return None

    print(f"✅ 로그인 성공! {row[1]} 계정")
    return row[0], row[1]


# ================================
# 메인 메뉴
# ================================
def user_menu(user_id):
    while True:
        print("\n=== User Menu ===")
        print("1. 보드게임 등록")
        print("2. 보드게임 추천")
        print("3. 모임 검색 및 참여")
        print("4. 중고거래 등록")
        print("5. 중고거래 검색")
        print("6. 중고거래 승인")
        print("0. 로그아웃")

        choice = input("선택: ")

        if choice == "1":
            register_game(user_id)
        elif choice == "2":
            recommend_games()
        elif choice == "3":
            search_gatherings()
            join_gathering(user_id)
        elif choice == "4":
            register_sale(user_id)
        elif choice == "5":
            search_market(user_id)
        elif choice == "6":
            approve_trade(user_id)
        elif choice == "0":
            print("로그아웃합니다.")
            break
        else:
            print("잘못된 입력입니다.")


# ================================
# 시스템 시작
# ================================
def start():
    print("=== BoardGame Community System ===")

    while True:
        print("\n1. 로그인")
        print("2. 회원가입")
        print("0. 종료")
        choice = input("선택: ")

        if choice == "1":
            result = login()
            if result:
                user_menu(result[0])
        elif choice == "2":
            sign_up()
        elif choice == "0":
            print("종료합니다.")
            break
        else:
            print("잘못된 입력입니다.")


# ================================
# 보드게임 등록
# ================================
def register_game(user_id):
    con = sqlite3.connect("boardgame.db")
    cur = con.cursor()

    print("\n=== 보드게임 등록 ===")
    title = input("게임 이름: ")

    cur.execute("SELECT game_id FROM BoardGame_Master WHERE title=?", (title,))
    row = cur.fetchone()

    if row:
        game_id = row[0]
        print(f"📌 이미 존재하는 게임입니다. game_id={game_id}")
    else:
        print("새 게임 정보 입력")
        genre = input("장르: ")
        min_p = input("최소 인원: ")
        max_p = input("최대 인원: ")
        playtime = input("평균 플레이 시간: ")
        diff = input("난이도: ")

        cur.execute("""
            INSERT INTO BoardGame_Master (title, genre, min_players, max_players, avg_playtime, difficulty)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, genre, min_p, max_p, playtime, diff))
        con.commit()

        cur.execute("SELECT last_insert_rowid()")
        game_id = cur.fetchone()[0]
        print(f"📌 새 게임 등록 완료! game_id={game_id}")

    cond = input("게임 상태(A/B/C): ").upper()
    if cond not in ["A", "B", "C"]:
        cond = "A"

    cur.execute("""
        INSERT INTO User_Collection (owner_id, game_id, condition_rank)
        VALUES (?, ?, ?)
    """, (user_id, game_id, cond))

    con.commit()
    con.close()
    print("✅ 보드게임 등록 완료!")


# ================================
# 보드게임 추천
# ================================
def recommend_games():
    con = sqlite3.connect("boardgame.db")
    cur = con.cursor()

    print("\n=== 보드게임 추천 ===")
    genre = input("장르 검색(엔터=전체): ")
    players = input("플레이 인원(엔터=전체): ")
    max_diff = input("최대 난이도(엔터=5): ")

    if players.strip() == "":
        players = None
    else:
        players = int(players)

    if max_diff.strip() == "":
        max_diff = 5.0
    else:
        max_diff = float(max_diff)

    query = """
        SELECT title, genre, min_players, max_players, avg_playtime, difficulty
        FROM BoardGame_Master
        WHERE difficulty <= ?
    """
    params = [max_diff]

    if genre.strip():
        query += " AND genre LIKE ?"
        params.append('%' + genre + '%')

    if players:
        query += " AND min_players <= ? AND max_players >= ?"
        params += [players, players]

    query += " ORDER BY difficulty ASC"

    cur.execute(query, params)
    rows = cur.fetchall()

    if not rows:
        print("❌ 없음")
        con.close()
        return

    print("\n📌 추천 목록:")
    for r in rows:
        print(f"- {r[0]} | {r[1]} | {r[2]}~{r[3]}명 | {r[4]}분 | 난이도:{r[5]}")

    con.close()


# ================================
# 모임 검색
# ================================
def search_gatherings():
    con = sqlite3.connect("boardgame.db")
    cur = con.cursor()

    print("\n=== 모임 검색 ===")
    loc = input("지역(엔터=전체): ")
    date = input("날짜(YYYY-MM-DD, 엔터=전체): ")
    min_p = input("최소 모집 인원(엔터=전체): ")

    query = """
        SELECT meeting_id, title, location, meet_date,
               max_participants, current_participants, status
        FROM Gathering
        WHERE 1=1
    """
    params = []

    if loc.strip():
        query += " AND location LIKE ?"
        params.append('%' + loc + '%')

    if date.strip():
        query += " AND date(meet_date)=?"
        params.append(date)

    if min_p.strip():
        query += " AND max_participants >= ?"
        params.append(min_p)

    query += " ORDER BY meet_date ASC"

    cur.execute(query, params)
    rows = cur.fetchall()

    if not rows:
        print("❌ 모임 없음")
    else:
        print("\n📌 모임 검색 결과:")
        for r in rows:
            print(f"[{r[0]}] {r[1]} | {r[2]} | {r[3]} | {r[5]}/{r[4]}명")

    con.close()


# ================================
# 모임 참여
# ================================
def join_gathering(user_id):
    con = sqlite3.connect("boardgame.db")
    cur = con.cursor()

    print("\n=== 모임 참여 ===")
    meeting_id = input("참여할 모임 ID 입력: ")

    try:
        con.execute("BEGIN")

        cur.execute("""
            SELECT max_participants, current_participants
            FROM Gathering WHERE meeting_id=?
        """, (meeting_id,))
        row = cur.fetchone()

        if not row:
            print("❌ 모임 없음")
            return

        max_p, cur_p = row

        cur.execute("""
            SELECT status FROM Gathering_Participants
            WHERE meeting_id=? AND user_id=?
        """, (meeting_id, user_id))
        if cur.fetchone():
            print("❌ 이미 참여 신청함")
            return

        if cur_p >= max_p:
            status = "Waitlist"
            print("⚠️ 정원 초과 → 대기자 등록")
        else:
            status = "Approved"
            cur.execute("""
                UPDATE Gathering
                SET current_participants = current_participants + 1
                WHERE meeting_id=?
            """, (meeting_id,))
            print("👍 참여 승인 완료")

        cur.execute("""
            INSERT INTO Gathering_Participants (meeting_id, user_id, status)
            VALUES (?, ?, ?)
        """, (meeting_id, user_id, status))

        con.commit()
        print("✅ 처리 완료")

    except Exception as e:
        con.rollback()
        print("❌ 오류:", e)

    finally:
        con.close()


# ================================
# 중고거래 등록
# ================================
def register_sale(user_id):
    con = sqlite3.connect("boardgame.db")
    cur = con.cursor()

    print("\n=== 중고거래 등록 ===")

    cur.execute("""
        SELECT UC.collection_id, BM.title, UC.condition_rank
        FROM User_Collection UC
        JOIN BoardGame_Master BM ON UC.game_id=BM.game_id
        WHERE UC.owner_id=? AND UC.status='Available'
    """, (user_id,))

    rows = cur.fetchall()

    if not rows:
        print("❌ 판매 가능한 게임 없음")
        con.close()
        return

    print("\n📌 판매 가능 목록:")
    for r in rows:
        print(f"{r[0]}. {r[1]} (상태:{r[2]})")

    col_id = input("판매할 collection_id: ")

    cur.execute("""
        SELECT collection_id FROM User_Collection
        WHERE collection_id=? AND owner_id=? AND status='Available'
    """, (col_id, user_id))

    if not cur.fetchone():
        print("❌ 잘못된 선택")
        con.close()
        return

    price = input("가격: ")
    desc = input("설명: ")

    cur.execute("""
        INSERT INTO Market_Listing (collection_id, seller_id, price, description)
        VALUES (?, ?, ?, ?)
    """, (col_id, user_id, price, desc))

    cur.execute("""
        UPDATE User_Collection
        SET status='In_Trade'
        WHERE collection_id=?
    """, (col_id,))

    con.commit()
    con.close()
    print("📌 중고거래 등록 완료!")


# ================================
# 중고거래 검색 (구매 신청만)
# ================================
def search_market(user_id):
    con = sqlite3.connect("boardgame.db")
    cur = con.cursor()

    print("\n=== 중고거래 검색 ===")
    title = input("게임 이름(엔터=전체): ")

    query = """
        SELECT ML.listing_id, BM.title, BM.genre,
               UC.collection_id, UC.condition_rank,
               ML.price, ML.description, U.username, ML.seller_id
        FROM Market_Listing ML
        JOIN User_Collection UC ON ML.collection_id=UC.collection_id
        JOIN BoardGame_Master BM ON UC.game_id=BM.game_id
        JOIN User U ON ML.seller_id=U.user_id
        WHERE UC.status='In_Trade'
    """
    params = []

    if title.strip():
        query += " AND BM.title LIKE ?"
        params.append('%' + title + '%')

    cur.execute(query, params)
    rows = cur.fetchall()

    if not rows:
        print("❌ 거래 없음")
        con.close()
        return

    print("\n📌 검색 결과:")
    for r in rows:
        print(f"[{r[0]}] {r[1]} | {r[2]} | 상태:{r[4]} | 가격:{r[5]} | 판매자:{r[7]}")

    select_id = input("\n구매 신청할 리스트ID (0=취소): ")
    if select_id == "0":
        con.close()
        return

    matched = None
    for r in rows:
        if str(r[0]) == select_id:
            matched = r
            break

    if not matched:
        print("❌ 잘못된 리스트ID")
        con.close()
        return

    listing_id = matched[0]

    cur.execute("""
        UPDATE Market_Listing
        SET buyer_id = ?
        WHERE listing_id = ?
    """, (user_id, listing_id))

    con.commit()
    con.close()
    print("📌 구매 신청 완료! (판매자의 승인 필요)")


# ================================
# 판매자가 거래 승인
# ================================
def approve_trade(user_id):
    con = sqlite3.connect("boardgame.db")
    cur = con.cursor()

    print("\n=== 중고거래 승인 ===")

    cur.execute("""
        SELECT ML.listing_id, ML.buyer_id, ML.price,
               UC.collection_id
        FROM Market_Listing ML
        JOIN User_Collection UC
        ON ML.collection_id=UC.collection_id
        WHERE ML.seller_id=? AND ML.buyer_id IS NOT NULL
    """, (user_id,))

    rows = cur.fetchall()

    if not rows:
        print("📌 승인 대기 없음")
        con.close()
        return

    print("\n📌 승인 요청 목록:")
    for r in rows:
        print(f"리스트ID:{r[0]} | 구매자ID:{r[1]} | 가격:{r[2]}")

    listing_id = input("\n승인할 리스트ID 입력: ")

    target = None
    for r in rows:
        if str(r[0]) == listing_id:
            target = r
            break

    if not target:
        print("❌ 잘못된 리스트ID")
        con.close()
        return

    buyer_id = target[1]
    price = target[2]
    collection_id = target[3]

    cur.execute("""
        INSERT INTO Trade_Log (listing_id, seller_id, buyer_id, final_price)
        VALUES (?, ?, ?, ?)
    """, (listing_id, user_id, buyer_id, price))

    cur.execute("""
        UPDATE User_Collection
        SET owner_id=?, status='Sold'
        WHERE collection_id=?
    """, (buyer_id, collection_id))

    cur.execute("DELETE FROM Market_Listing WHERE listing_id=?", (listing_id,))

    con.commit()
    con.close()
    print("✅ 거래 승인 → 거래 완료!")


# ================================
# 실행
# ================================
if __name__ == "__main__":
    start()

import sqlite3
import pandas as pd


class BoardLinkDB:
    def __init__(self, db_path="boardgame.db"):
        self.db_path = db_path
        self.init_tables()

    def init_tables(self):
        conn = self.get_connection()
        cur = conn.cursor()

        cur.executescript("""
        CREATE TABLE IF NOT EXISTS User (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            location_info TEXT,
            role TEXT DEFAULT 'User',
            likes_count INTEGER DEFAULT 0,
            dislikes_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS BoardGame_Master (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            genre TEXT,
            min_players INTEGER,
            max_players INTEGER,
            avg_playtime INTEGER,
            difficulty REAL
        );

        CREATE TABLE IF NOT EXISTS User_Collection (
            collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            game_id INTEGER,
            condition_rank TEXT,
            status TEXT,
            FOREIGN KEY(owner_id) REFERENCES User(user_id),
            FOREIGN KEY(game_id) REFERENCES BoardGame_Master(game_id)
        );

        CREATE TABLE IF NOT EXISTS Gathering (
            meeting_id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_id INTEGER,
            title TEXT,
            description TEXT,
            location TEXT,
            meet_date TEXT,
            max_participants INTEGER,
            current_participants INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Open',
            FOREIGN KEY(host_id) REFERENCES User(user_id)
        );

        CREATE TABLE IF NOT EXISTS Gathering_Participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER,
            user_id INTEGER,
            status TEXT,
            wait_order INTEGER,
            FOREIGN KEY(meeting_id) REFERENCES Gathering(meeting_id),
            FOREIGN KEY(user_id) REFERENCES User(user_id)
        );

        CREATE TABLE IF NOT EXISTS Market_Listing (
            listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER,
            seller_id INTEGER,
            buyer_id INTEGER,
            price INTEGER,
            description TEXT,
            status TEXT DEFAULT 'Open',
            seller_account TEXT,
            buyer_address TEXT,
            FOREIGN KEY(collection_id) REFERENCES User_Collection(collection_id),
            FOREIGN KEY(seller_id) REFERENCES User(user_id),
            FOREIGN KEY(buyer_id) REFERENCES User(user_id)
        );

        CREATE TABLE IF NOT EXISTS Trade_Log (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            seller_id INTEGER,
            buyer_id INTEGER,
            final_price INTEGER
        );

        CREATE TABLE IF NOT EXISTS Review (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            writer_id INTEGER,
            target_user INTEGER,
            trade_id INTEGER,
            meeting_id INTEGER,
            mode TEXT,
            rating INTEGER,
            content TEXT
        );

        CREATE TABLE IF NOT EXISTS Role_Request (
            req_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            current_role TEXT,
            request_role TEXT,
            status TEXT DEFAULT 'Pending'
        );
        """)

        conn.commit()
        conn.close()


    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def run_query(self, query, params=()):
        conn = self.get_connection()
        try:
            return pd.read_sql(query, conn, params=params)
        finally:
            conn.close()

    def execute_query(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # ==========================
    # 1. 인증 (Auth)
    # ==========================
    def login(self, username, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, role, username FROM User WHERE username=? AND password_hash=?", (username, password))
        row = cursor.fetchone()
        conn.close()
        return row

    def sign_up(self, username, password, location):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM User WHERE username=?", (username,))
        if cursor.fetchone():
            conn.close()
            return False, "이미 존재하는 ID입니다."

        try:
            cursor.execute(
                "INSERT INTO User (username, password_hash, location_info, role) VALUES (?, ?, ?, 'User')", (username, password, location))
            conn.commit()
            return True, "회원가입 완료!"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def get_user_info(self, user_id):
        return self.run_query("SELECT * FROM User WHERE user_id = ?", (user_id,))

    # ==========================
    # 2. 보드게임 (Game & Collection)
    # ==========================
    def get_my_collection(self, user_id):
        query = """
            SELECT UC.collection_id, BM.title, BM.genre, UC.condition_rank, UC.status
            FROM User_Collection UC
            JOIN BoardGame_Master BM ON UC.game_id = BM.game_id
            WHERE UC.owner_id = ?
        """
        return self.run_query(query, (user_id,))

    def register_game_to_collection(self, user_id, title, condition, genre, min_p, max_p, time, diff):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 게임 마스터 확인/등록
            cursor.execute(
                "SELECT game_id FROM BoardGame_Master WHERE title=?", (title,))
            row = cursor.fetchone()
            if row:
                game_id = row[0]
            else:
                cursor.execute("""
                    INSERT INTO BoardGame_Master (title, genre, min_players, max_players, avg_playtime, difficulty)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (title, genre, min_p, max_p, time, diff))
                game_id = cursor.lastrowid

            # 컬렉션 등록
            cursor.execute(
                "INSERT INTO User_Collection (owner_id, game_id, condition_rank) VALUES (?, ?, ?)", (user_id, game_id, condition))
            conn.commit()
            return True, "등록 완료"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    # ==========================
    # 3. 모임 (Gathering)
    # ==========================
    def search_gatherings(self, loc=None):
        # description 컬럼도 조회하도록 추가
        query = """
            SELECT G.meeting_id, G.title, G.description, G.location, G.meet_date, 
                   G.current_participants, G.max_participants, G.status, U.username as host_name
            FROM Gathering G
            JOIN User U ON G.host_id = U.user_id
        """
        params = []
        if loc:
            query += " WHERE G.location LIKE ?"
            params.append(f'%{loc}%')

        query += " ORDER BY CASE WHEN G.status='Open' THEN 1 ELSE 2 END, G.meet_date ASC"
        return self.run_query(query, params)

    # [수정됨] description 파라미터 추가
    def create_gathering(self, user_id, title, desc, loc, date_str, max_p):

        conn = self.get_connection()
        cur = conn.cursor()

        try:
            # ✅ 1) Gathering 생성 + 현재인원 1로 시작
            cur.execute("""
                INSERT INTO Gathering
                (host_id, title, description, location, meet_date,
                max_participants, current_participants, status)
                VALUES (?, ?, ?, ?, ?, ?, 1, 'Open')
            """, (user_id, title, desc, loc, date_str, max_p))

            # ✅ 새로 생성된 meeting_id 가져오기
            meeting_id = cur.lastrowid

            # ✅ 2) 만든 사람 본인을 참가자로 자동 등록
            cur.execute("""
                INSERT INTO Gathering_Participants
                (meeting_id, user_id, status, wait_order)
                VALUES (?, ?, 'Approved', 0)
            """, (meeting_id, user_id))

            conn.commit()
            return True, "모임 개설 완료"

        except Exception as e:
            conn.rollback()
            return False, str(e)

        finally:
            conn.close()


    def join_gathering(self, user_id, meeting_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT status FROM Gathering WHERE meeting_id=?", (meeting_id,))
            row = cursor.fetchone()
            if not row:
                return False, "모임이 없습니다."
            if row[0] != 'Open':
                return False, "이미 종료된 모임입니다."

            cursor.execute("SELECT role FROM User WHERE user_id=?", (user_id,))
            role = cursor.fetchone()[0]

            cursor.execute(
                "SELECT 1 FROM Gathering_Participants WHERE meeting_id=? AND user_id=?", (meeting_id, user_id))
            if cursor.fetchone():
                return False, "이미 신청했습니다."

            cursor.execute(
                "SELECT COALESCE(MAX(wait_order), 0) FROM Gathering_Participants WHERE meeting_id=? AND status='Waitlist'", (meeting_id,))
            max_order = cursor.fetchone()[0]

            if role == "BadUser":
                my_order = max_order + 1
                msg = "BadUser: 대기열 최하위 배정"
            elif role == "VIP":
                cursor.execute(
                    "UPDATE Gathering_Participants SET wait_order = wait_order + 1 WHERE meeting_id=? AND status='Waitlist'", (meeting_id,))
                my_order = 1
                msg = "VIP: 대기열 1순위 배정"
            else:
                my_order = max_order + 1
                msg = f"대기열 {my_order}번 배정"

            cursor.execute(
                "INSERT INTO Gathering_Participants (meeting_id, user_id, status, wait_order) VALUES (?, ?, 'Waitlist', ?)", (meeting_id, user_id, my_order))
            conn.commit()
            return True, msg
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def get_my_hosted_gatherings(self, host_id):
        return self.run_query("SELECT * FROM Gathering WHERE host_id=? ORDER BY meet_date DESC", (host_id,))

    def get_gathering_applicants(self, meeting_id):
        query = """
            SELECT GP.user_id, U.username, U.role, U.likes_count, U.dislikes_count, GP.status, GP.wait_order
            FROM Gathering_Participants GP
            JOIN User U ON GP.user_id = U.user_id
            WHERE GP.meeting_id = ? AND GP.status = 'Waitlist'
            ORDER BY GP.wait_order ASC
        """
        return self.run_query(query, (meeting_id,))

    def get_gathering_approved_members(self, meeting_id):
        """
        모임에 'Approved' 상태로 확정된 참가자 목록 조회
        (호스트 화면에서 확인용)
        """
        query = """
            SELECT GP.user_id, U.username, U.role,
                   U.likes_count, U.dislikes_count
            FROM Gathering_Participants GP
            JOIN User U ON GP.user_id = U.user_id
            WHERE GP.meeting_id = ? AND GP.status = 'Approved'
            ORDER BY U.username ASC
        """
        return self.run_query(query, (meeting_id,))

    def approve_gathering_participant(self, meeting_id, target_user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT max_participants, current_participants FROM Gathering WHERE meeting_id=?", (meeting_id,))
            mx, cur = cursor.fetchone()
            if cur >= mx:
                return False, "정원 초과"

            cursor.execute(
                "UPDATE Gathering_Participants SET status='Approved' WHERE meeting_id=? AND user_id=?", (meeting_id, target_user_id))
            if cursor.rowcount > 0:
                cursor.execute(
                    "UPDATE Gathering SET current_participants = current_participants + 1 WHERE meeting_id=?", (meeting_id,))
                conn.commit()
                return True, "승인 완료"
            return False, "대상자를 찾을 수 없음"
        finally:
            conn.close()

    def reject_gathering_participant(self, meeting_id, target_user_id):
        return self.execute_query("UPDATE Gathering_Participants SET status='Rejected' WHERE meeting_id=? AND user_id=?", (meeting_id, target_user_id))

    def close_gathering(self, meeting_id):
        return self.execute_query("UPDATE Gathering SET status='Closed' WHERE meeting_id=?", (meeting_id,))

    def get_my_applications(self, user_id):
        query = """
            SELECT G.title, G.meet_date, G.location, GP.status, GP.wait_order
            FROM Gathering_Participants GP
            JOIN Gathering G ON GP.meeting_id = G.meeting_id
            WHERE GP.user_id = ?
            ORDER BY G.meet_date DESC
        """
        return self.run_query(query, (user_id,))

    # ==========================
    # 4. 중고 거래 (Market)
    # ==========================
    def register_market(self, user_id, col_id, price, desc):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT role FROM User WHERE user_id=?", (user_id,))
            if cursor.fetchone()[0] == "BadUser":
                return False, "BadUser는 판매 불가"
            cursor.execute(
                "INSERT INTO Market_Listing (collection_id, seller_id, price, description) VALUES (?, ?, ?, ?)", (col_id, user_id, price, desc))
            cursor.execute(
                "UPDATE User_Collection SET status='In_Trade' WHERE collection_id=?", (col_id,))
            conn.commit()
            return True, "판매 등록 완료"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def get_market_list(self):
        query = """
            SELECT
                BM.title            AS game_title,      -- 게임명
                ML.price            AS price,           -- 가격
                ML.description      AS description,     -- 설명
                UC.condition_rank   AS condition_rank,  -- 상태(A/B/C)
                ML.status           AS trade_status,    -- 거래상태
                U.username          AS seller           -- 판매자
            FROM Market_Listing ML
            JOIN User_Collection UC ON ML.collection_id = UC.collection_id
            JOIN BoardGame_Master BM ON UC.game_id = BM.game_id
            JOIN User U ON ML.seller_id = U.user_id
            WHERE
                ML.buyer_id IS NULL
                AND UC.status = 'In_Trade'
            ORDER BY ML.listing_id DESC
        """
        return self.run_query(query)


    def request_purchase(self, user_id, listing_id):
        return self.execute_query("UPDATE Market_Listing SET buyer_id=?, status='Requested' WHERE listing_id=?", (user_id, listing_id))

    def approve_trade_request(self, listing_id):
        return self.execute_query("UPDATE Market_Listing SET status='Approved' WHERE listing_id=?", (listing_id,))

    def get_ongoing_trades(self, user_id):
        query = """
            SELECT listing_id, status, seller_id, buyer_id, seller_account, buyer_address
            FROM Market_Listing
            WHERE (seller_id=? OR buyer_id=?) AND status IN ('Approved', 'Paid')
        """
        return self.run_query(query, (user_id, user_id))

    def update_trade_info(self, listing_id, user_id, info_type, value):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            col = "seller_account" if info_type == 'account' else "buyer_address"
            cursor.execute(
                f"UPDATE Market_Listing SET {col}=? WHERE listing_id=?", (value, listing_id))
            cursor.execute(
                "SELECT seller_account, buyer_address FROM Market_Listing WHERE listing_id=?", (listing_id,))
            acc, addr = cursor.fetchone()
            msg = "정보 입력 완료"
            if acc and addr:
                cursor.execute(
                    "UPDATE Market_Listing SET status='Paid' WHERE listing_id=?", (listing_id,))
                msg += " -> 양측 입력 확인됨! 입금(Paid) 상태로 전환."
            conn.commit()
            return True, msg
        finally:
            conn.close()

    def complete_trade_transaction(self, listing_id, seller_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT collection_id, buyer_id, price FROM Market_Listing WHERE listing_id=? AND status='Paid'", (listing_id,))
            row = cursor.fetchone()
            if not row:
                return False, "완료 가능한 거래가 아닙니다."
            cid, buyer, price = row
            cursor.execute("INSERT INTO Trade_Log (listing_id, seller_id, buyer_id, final_price) VALUES (?, ?, ?, ?)",
                           (listing_id, seller_id, buyer, price))
            cursor.execute(
                "UPDATE User_Collection SET owner_id=?, status='Sold' WHERE collection_id=?", (buyer, cid))
            cursor.execute(
                "DELETE FROM Market_Listing WHERE listing_id=?", (listing_id,))
            conn.commit()
            return True, "거래가 최종 완료되었습니다!"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    # ==========================
    # 5. 리뷰 & 평판
    # ==========================
    def _check_auto_downgrade(self, cursor, user_id):

    # ===============================
    # ✅ admin 계정은 무조건 Admin 유지
    # ===============================
        cursor.execute(
            "SELECT username, role FROM User WHERE user_id=?",
            (user_id,)
        )
        username, role = cursor.fetchone()

        if username.lower() == "admin":
            if role != "Admin":
                cursor.execute(
                    "UPDATE User SET role='Admin' WHERE user_id=?",
                    (user_id,)
                )
            return

    # ===============================
    # ✅ 강등 전용 로직
    # ===============================

        cursor.execute(
            "SELECT likes_count, dislikes_count FROM User WHERE user_id=?",
            (user_id,)
        )

        likes, dislikes = cursor.fetchone()
        score = likes - dislikes

        new_role = role

    # VIP → User
        if role == "VIP" and score < 8:
            new_role = "User"

    # User → BadUser
        elif role == "User" and score < 0:
            new_role = "BadUser"

    # role 변경 반영
        if new_role != role:
            cursor.execute(
                "UPDATE User SET role=? WHERE user_id=?",
                (new_role, user_id)
            )



    def get_pending_trade_reviews(self, user_id):
        query = """
            SELECT
                TL.trade_id,
                BM.title AS game_title,

                CASE
                    WHEN TL.seller_id = ? THEN U2.username
                    ELSE U.username
                END AS target_user

            FROM Trade_Log TL
            JOIN User_Collection UC ON TL.listing_id = UC.collection_id
            JOIN BoardGame_Master BM ON UC.game_id = BM.game_id

            JOIN User U  ON TL.seller_id = U.user_id
            JOIN User U2 ON TL.buyer_id  = U2.user_id

            WHERE (TL.seller_id = ? OR TL.buyer_id = ?)
                AND NOT EXISTS (
                    SELECT 1 FROM Review R
                    WHERE R.trade_id = TL.trade_id
                        AND R.writer_id = ?
                        AND R.mode = 'Trade'
                )
        """
        return self.run_query(query, (user_id, user_id, user_id, user_id))

    def get_pending_event_reviews(self, user_id):
        """
        내가 참여 완료한 모임에서
        자기 자신을 제외한 모든 Approved 인원 평가 리스트 반환
        """
        q = """
            SELECT
                G.meeting_id,
                G.title AS meeting_title,
                U.username AS host_name

            FROM Gathering_Participants GP1

            JOIN Gathering G
                ON GP1.meeting_id = G.meeting_id

            JOIN Gathering_Participants GP2
                ON GP2.meeting_id = G.meeting_id

            JOIN User U
                ON GP2.user_id = U.user_id

            WHERE GP1.user_id = ?
            AND GP1.status = 'Approved'

            AND GP2.status = 'Approved'
            AND GP2.user_id != ?

            AND NOT EXISTS (
                SELECT 1 FROM Review R
                WHERE R.mode='Event'
                AND R.writer_id=?
                AND R.target_user=GP2.user_id
                AND R.meeting_id=G.meeting_id
            )

            ORDER BY G.meet_date DESC
        """
        return self.run_query(q, (user_id, user_id, user_id))


    def get_user_id_by_username(self, username):
        q = "SELECT user_id FROM User WHERE username=?"
        row = self.run_query(q, (username,))
        if row.empty:
            return None
        return row.iloc[0]["user_id"]

    def submit_review(self, writer_id, target_user, trade_id=None, meeting_id=None, mode="Trade", rating=1):
        conn = self.get_connection()
        cur = conn.cursor()

        try:
            # ✅ ✅ 직접 cursor로 lookup
            cur.execute("SELECT user_id FROM User WHERE username=?", (target_user,))
            r = cur.fetchone()

            if not r:
                return False, "대상 유저를 찾을 수 없습니다."

            target_user_id = r[0]

            # 리뷰 저장
            cur.execute("""
                INSERT INTO Review
                (writer_id, target_user, trade_id, meeting_id, mode, rating, content)
                VALUES (?, ?, ?, ?, ?, ?, NULL)
            """, (writer_id, target_user_id, trade_id, meeting_id, mode, rating))


            # 평판 반영
            if rating == 1:
                cur.execute(
                    "UPDATE User SET likes_count = likes_count + 1 WHERE user_id=?",
                    (target_user_id,)
                )
            else:
                cur.execute(
                    "UPDATE User SET dislikes_count = dislikes_count + 1 WHERE user_id=?",
                    (target_user_id,)
                )

            self._check_auto_downgrade(cur, target_user_id)

            conn.commit()
            return True, "평가 완료"

        except Exception as e:
            conn.rollback()
            return False, str(e)

        finally:
            conn.close()
    
    def rerun_auto_role_check(self):
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT user_id FROM User")
        users = cur.fetchall()

        for (uid,) in users:
            self._check_auto_downgrade(cur, uid)

        conn.commit()
        conn.close()


    def request_role_change(self, user_id, to_role):
        """
        등급 변경 신청 (User→VIP, BadUser→User 등)
        """
        conn = self.get_connection()
        cur = conn.cursor()
        try:
            # 현재 역할 조회
            cur.execute("SELECT role FROM User WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            if not row:
                return False, "유저를 찾을 수 없습니다."
            from_role = row[0]

            # 이미 대기 중인 신청이 있는지 확인
            cur.execute(
                "SELECT 1 FROM Role_Request WHERE user_id=? AND status='Pending'",
                (user_id,)
            )
            if cur.fetchone():
                return False, "이미 진행 중인 등급 변경 신청이 있습니다."

            # 신청 등록
            cur.execute(
                "INSERT INTO Role_Request (user_id, from_role, to_role) VALUES (?, ?, ?)",
                (user_id, from_role, to_role)
            )
            conn.commit()
            return True, "등급 변경 신청이 접수되었습니다."

        except Exception as e:
            conn.rollback()
            return False, str(e)

        finally:
            conn.close()

    # ==========================
    # 6. 관리자
    # ==========================

    def get_all_users(self): return self.run_query("SELECT * FROM User")

    def delete_gathering_admin(self, meeting_id):
        conn = self.get_connection()
        try:
            conn.execute(
                "DELETE FROM Gathering_Participants WHERE meeting_id=?", (meeting_id,))
            conn.execute(
                "DELETE FROM Gathering WHERE meeting_id=?", (meeting_id,))
            conn.commit()
        finally:
            conn.close()

    def delete_listing_admin(self, listing_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT collection_id FROM Market_Listing WHERE listing_id=?", (listing_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "UPDATE User_Collection SET status='Available' WHERE collection_id=?", (row[0],))
            cursor.execute(
                "DELETE FROM Market_Listing WHERE listing_id=?", (listing_id,))
            conn.commit()
        finally:
            conn.close()

    def search_recommend_games(self, genre=None, players=None, max_time=None, max_diff=None):
        query = """
            SELECT title, genre, min_players, max_players, avg_playtime, difficulty
            FROM BoardGame_Master
            WHERE 1=1
        """
        params = []

        if genre:
            query += " AND genre LIKE ?"
            params.append(f"%{genre}%")

        if players:
            query += " AND min_players <= ? AND max_players >= ?"
            params.extend([players, players])

        if max_time:
            query += " AND avg_playtime <= ?"
            params.append(max_time)

        if max_diff:
            query += " AND difficulty <= ?"
            params.append(max_diff)

        query += " ORDER BY difficulty ASC, avg_playtime ASC"

        return self.run_query(query, params)
    
    def get_role_requests(self):
        query = """
            SELECT
                RR.req_id,
                U.username,
                RR.current_role,
                RR.request_role,
                RR.status
            FROM Role_Request RR
            JOIN User U ON RR.user_id = U.user_id
            WHERE RR.status = 'Pending'
            ORDER BY RR.req_id ASC
        """
        return self.run_query(query)

    
    def approve_role_request(self, req_id):
        """
        관리자용: 등급 변경 신청 승인
        """
        conn = self.get_connection()
        cur = conn.cursor()
        try:
            # 신청 정보 가져오기
            cur.execute(
                "SELECT user_id, to_role FROM Role_Request WHERE req_id=? AND status='Pending'",
                (req_id,)
            )
            row = cur.fetchone()
            if not row:
                return False, "대상 요청을 찾을 수 없습니다."

            user_id, new_role = row

            # User 테이블에 역할 반영
            cur.execute(
                "UPDATE User SET role=? WHERE user_id=?",
                (new_role, user_id)
            )

            # 신청 상태를 Approved로 변경
            cur.execute(
                "UPDATE Role_Request SET status='Approved' WHERE req_id=?",
                (req_id,)
            )

            conn.commit()
            return True, "등급 변경이 완료되었습니다."

        except Exception as e:
            conn.rollback()
            return False, str(e)

        finally:
            conn.close()

    def search_market(
        self,
        title=None,
        genre=None,
        max_price=None
    ):
        query = """
            SELECT
                ML.listing_id,
                BM.title,
                BM.genre,
                ML.price,
                ML.description,
                U.username,
                U.role,
                ML.status
            FROM Market_Listing ML
            JOIN User_Collection UC ON ML.collection_id = UC.collection_id
            JOIN BoardGame_Master BM ON UC.game_id = BM.game_id
            JOIN User U ON ML.seller_id = U.user_id
            WHERE ML.buyer_id IS NULL
            AND UC.status='In_Trade'
        """

        params = []

        if title:
            query += " AND BM.title LIKE ?"
            params.append(f"%{title}%")

        if genre:
            query += " AND BM.genre LIKE ?"
            params.append(f"%{genre}%")

        if max_price:
            query += " AND ML.price <= ?"
            params.append(max_price)

        query += " ORDER BY ML.listing_id DESC"

        return self.run_query(query, params)
    
    def search_gathering_filtered(
        self,
        keyword=None,
        location=None,
        date=None,
        status=None
    ):
        q = """
            SELECT G.*
            FROM Gathering G
            WHERE 1=1
        """
        p = []

        if keyword:
            q += " AND (G.title LIKE ? OR G.description LIKE ?)"
            p.extend([f"%{keyword}%", f"%{keyword}%"])

        if location:
            q += " AND G.location LIKE ?"
            p.append(f"%{location}%")

        if date:
            q += " AND G.meet_date >= ?"
            p.append(date)

        if status:
            q += " AND G.status=?"
            p.append(status)

        q += " ORDER BY meet_date ASC"

        return self.run_query(q, p)





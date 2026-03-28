import sqlite3
import os
from datetime import datetime

class DeerPipeDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 用户基础信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    total_times INTEGER DEFAULT 0,
                    last_reset_month TEXT
                )
            ''')
            # 签到记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS checkins (
                    user_id TEXT,
                    date TEXT, -- YYYY-MM-DD
                    count INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, date)
                )
            ''')
            # 助人签到记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS helper_records (
                    helper_id TEXT,
                    date TEXT, -- YYYY-MM-DD
                    count INTEGER DEFAULT 1,
                    PRIMARY KEY (helper_id, date)
                )
            ''')
            conn.commit()

    def get_user(self, user_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone()

    def update_user(self, user_id: str, username: str, total_delta: int = 1, reset_month: str = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 使用 INSERT OR IGNORE 初始化用户
            cursor.execute('INSERT OR IGNORE INTO users (user_id, username, total_times, last_reset_month) VALUES (?, ?, 0, ?)', 
                           (user_id, username, reset_month))
            # 更新用户名和总次数
            if reset_month:
                cursor.execute('UPDATE users SET username = ?, total_times = total_times + ?, last_reset_month = ? WHERE user_id = ?',
                               (username, total_delta, reset_month, user_id))
            else:
                cursor.execute('UPDATE users SET username = ?, total_times = total_times + ? WHERE user_id = ?',
                               (username, total_delta, user_id))
            conn.commit()

    def reset_total_times(self, user_id: str, reset_month: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET total_times = 0, last_reset_month = ? WHERE user_id = ?', (reset_month, user_id))
            conn.commit()

    def get_checkin(self, user_id: str, date: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT count FROM checkins WHERE user_id = ? AND date = ?', (user_id, date))
            res = cursor.fetchone()
            return res[0] if res else 0

    def add_checkin(self, user_id: str, date: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO checkins (user_id, date, count) VALUES (?, ?, 1)
                ON CONFLICT(user_id, date) DO UPDATE SET count = count + 1
            ''', (user_id, date))
            conn.commit()

    def remove_checkin(self, user_id: str, date: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM checkins WHERE user_id = ? AND date = ?', (user_id, date))
            conn.commit()

    def get_monthly_records(self, user_id: str, year_month: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 获取该月份的所有天数记录
            cursor.execute('SELECT date, count FROM checkins WHERE user_id = ? AND date LIKE ?', (user_id, year_month + '%'))
            return cursor.fetchall()

    def get_helper_count(self, helper_id: str, date: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT count FROM helper_records WHERE helper_id = ? AND date = ?', (helper_id, date))
            res = cursor.fetchone()
            return res[0] if res else 0

    def add_helper_record(self, helper_id: str, date: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO helper_records (helper_id, date, count) VALUES (?, ?, 1)
                ON CONFLICT(helper_id, date) DO UPDATE SET count = count + 1
            ''', (helper_id, date))
            conn.commit()

    def get_leaderboard(self, period_prefix: str = None, limit: int = 15):
        """
        获取排行榜。
        period_prefix: 
            None -> 总榜 (基于 users.total_times)
            'YYYY' -> 年榜 (基于 checkins 聚合)
            'YYYY-MM' -> 月榜 (基于 checkins 聚合)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if period_prefix is None:
                # 总榜：直接查询 users 表
                cursor.execute('SELECT username, total_times FROM users ORDER BY total_times DESC LIMIT ?', (limit,))
            else:
                # 周期榜：聚合 checkins 表并关联 users 获取用户名
                cursor.execute('''
                    SELECT u.username, SUM(c.count) as total_times
                    FROM users u
                    JOIN checkins c ON u.user_id = c.user_id
                    WHERE c.date LIKE ?
                    GROUP BY u.user_id
                    ORDER BY total_times DESC
                    LIMIT ?
                ''', (period_prefix + '%', limit))
            
            return cursor.fetchall()

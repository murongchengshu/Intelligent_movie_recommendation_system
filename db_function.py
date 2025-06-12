#数据库模组
import sqlite3
#文件正常关闭装饰器，即实现数据库的自动关闭功能
from contextlib import contextmanager

# 数据库连接配置
DATABASE = 'movies.db'

# 上下文管理器，确保每次数据库连接后自动关闭
@contextmanager
def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    yield connection
    connection.close()

# 创建电影表
def create_movies_table():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE, 
                rating REAL NOT NULL,
                category TEXT NOT NULL,
                comments TEXT NOT NULL 
            )
        ''')
        conn.commit()

# 插入一部电影数据
def insert_movie(title, rating, category,comments):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO movies (title, rating, category,comments)
            VALUES (?, ?, ?, ?)
        ''', (title, rating, category,comments))
        conn.commit()

# 获取所有电影
def get_all_movies():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM movies')
        return cursor.fetchall()


def get_movies_paginated(page=1, page_size=10):
    """
    分页获取电影数据。

    参数:
    - page (int): 当前页码 (从1开始)。
    - page_size (int): 每页显示的条目数。

    返回:
    - a tuple: (list of movies, total_pages)
    """
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row  # 让查询结果可以像字典一样通过列名访问
        cursor = conn.cursor()

        # 首先，计算总条目数和总页数
        cursor.execute('SELECT COUNT(*) FROM movies')
        total_items = cursor.fetchone()[0]
        # 计算总页数，使用 (a + b - 1) // b 的技巧来向上取整
        total_pages = (total_items + page_size - 1) // page_size

        # 计算偏移量 (OFFSET)
        offset = (page - 1) * page_size

        # 执行分页查询
        cursor.execute('SELECT id, title, rating, category FROM movies ORDER BY id LIMIT ? OFFSET ?',
                       (page_size, offset))
        movies = cursor.fetchall()

        return movies, total_pages
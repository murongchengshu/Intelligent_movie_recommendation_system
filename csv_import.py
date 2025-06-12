# csv_import.py
import sqlite3
import csv
from db_function import *


def import_from_csv(file_path, progress_callback=None):
    """
    从用户指定的CSV文件路径导入数据。

    参数:
    - file_path (str): CSV文件的完整路径。
    - progress_callback (function): 用于报告进度的回调函数。
    """

    # 定义一个安全的报告函数
    def report(message):
        if progress_callback:
            progress_callback(message)
        else:
            print(message)

    report(f"准备从 '{file_path}' 文件导入数据...")
    try:
        # 确保表已创建
        create_movies_table()

        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            inserted_count = 0
            processed_count = 0

            # 先读取所有行，以便报告总进度
            rows = list(csv_reader)
            total_rows = len(rows)
            report(f"文件包含 {total_rows} 行数据，开始处理...")

            for i, row in enumerate(rows):
                processed_count += 1
                try:
                    # 注意：这里的列名可能需要根据不同的CSV文件进行调整
                    # 这是一个常见的挑战，暂时我们假设列名是固定的
                    title = row['title '].strip()
                    rating = float(row['star '].strip())
                    category = row['all_tags'].strip()
                    comment = row['description'].strip()

                    # 使用我们之前优化过的 insert_movie，它能处理重复数据
                    # 为了获取反馈，我们不能直接调用，而是需要用 get_db_connection
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT OR IGNORE INTO movies (title, rating, category, comments)
                            VALUES (?, ?, ?, ?)
                        ''', (title, rating, category, comment))
                        if cursor.rowcount > 0:
                            inserted_count += 1
                        conn.commit()

                    # 每处理10%的行数，报告一次进度
                    if (i + 1) % (total_rows // 10 + 1) == 0:
                        report(f"处理进度: {i + 1}/{total_rows}")

                except KeyError as e:
                    report(f"警告：CSV文件中缺少列 {e}，已跳过第 {i + 1} 行。")
                    continue
                except Exception as e:
                    report(f"导入行 '{row.get('title ', 'N/A')}' 时出错: {e}, 已跳过。")

        report(f"CSV数据导入完成！共处理 {processed_count} 行，成功插入 {inserted_count} 条新数据。")

    except FileNotFoundError:
        report(f"错误：文件 '{file_path}' 未找到。")
    except Exception as e:
        report(f"导入过程中发生未知错误: {e}")
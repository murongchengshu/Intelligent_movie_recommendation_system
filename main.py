#! /usr/bin/python
# -*- coding: UTF-8 -*-
# main.py
import csv
import os
import db_function
from csv_import import *
import crawler
from recommend import MovieRecommender
import pandas as pd


def clear_screen():
    """清空控制台屏幕"""
    os.system('cls' if os.name == 'nt' else 'clear')


def initialize_database():
    """删除旧数据库（如果存在）并创建新表"""
    if os.path.exists(db_function.DATABASE):
        os.remove(db_function.DATABASE)
        print(f"旧数据库 '{db_function.DATABASE}' 已删除。")
    db_function.create_movies_table()
    print("数据库和 'movies' 表已成功创建。")


def run_recommender():
    """运行推荐系统交互"""
    print("--- 电影智能推荐系统 ---")
    # 实例化推荐器，它会自动加载数据和构建模型
    recommender_system = MovieRecommender()

    # 如果模型没有成功构建（例如数据库为空），则直接退出
    if recommender_system.df is None or recommender_system.df.empty:
        print("\n无法启动推荐服务，请先向数据库中添加数据。")
        return

    while True:
        movie_title = input("\n请输入一部你喜欢的电影名称 (输入 'q' 退出): ").strip()
        if movie_title.lower() == 'q':
            break

        recommendations = recommender_system.get_recommendations(movie_title, top_n=5)

        if isinstance(recommendations, str):
            # 如果返回的是错误信息字符串
            print(recommendations)
        else:
            print(f"\n为你推荐与《{movie_title}》相似的电影：")
            print(recommendations.to_string())


def show_database_content():
    """
    分页显示数据库中的电影内容。
    """
    current_page = 1
    page_size = 15  # 每页显示15条

    while True:
        clear_screen()
        # 调用我们新创建的分页函数
        movies, total_pages = db_function.get_movies_paginated(page=current_page, page_size=page_size)

        if not movies:
            print("数据库为空，或已超出最大页数。")
        else:
            print("--- 数据库电影列表 ---")
            # 创建一个DataFrame来利用pandas的对齐打印功能
            df = pd.DataFrame(movies, columns=['id', 'title', 'rating', 'category'])
            # 我们不希望打印DataFrame的索引，所以设置 index=False
            print(df.to_string(index=False))
            print("-" * 60)
            print(f"第 {current_page} / {total_pages} 页")

        print("\n操作: [n] 下一页, [p] 上一页, [q] 退出")
        action = input("请输入你的操作: ").lower()

        if action == 'n':
            if current_page < total_pages:
                current_page += 1
        elif action == 'p':
            if current_page > 1:
                current_page -= 1
        elif action == 'q':
            break
        else:
            input("无效操作，按回车键继续...")


def main_menu():
    """显示主菜单并处理用户输入"""
    while True:
        clear_screen()
        print("=" * 30)
        print("      智能电影推荐系统菜单")
        print("=" * 30)
        print("1. 初始化/重置数据库")
        print("2. 从 top250.csv 导入数据")
        print("3. 从网站爬取数据 (最多47页)")
        print("4. 启动电影推荐服务")
        print("5. 查看数据库内容")
        print("6.退出")
        print("-" * 30)

        choice = input("请输入你的选择 [1-6]: ")

        if choice == '1':
            initialize_database()
            input("\n按回车键返回主菜单...")
        elif choice == '2':
            csv_import()
        elif choice == '3':
            while True:
                try:
                    pages_to_crawl = input("请输入你想爬取的页数 (例如: 5, 输入 'q' 返回): ")
                    if pages_to_crawl.lower() == 'q':
                        break  # 返回主菜单

                    num_pages = int(pages_to_crawl)
                    if num_pages > 0:
                        print("开始执行爬取任务...")
                        db_function.create_movies_table()
                        # 调用我们新的爬虫函数，并传入用户输入的页数
                        crawler.pachong(num_pages)
                        break  # 爬取完成，退出循环
                    else:
                        print("请输入一个大于0的整数。")
                except ValueError:
                    print("无效的输入，请输入一个数字。")

            input("\n按回车键返回主菜单...")
        elif choice == '4':
            run_recommender()
            input("\n推荐服务结束，按回车键返回主菜单...")
        elif choice == '5':
            show_database_content()
            # 从show_database_content退出后会自动返回主菜单，无需额外input

        elif choice == '6':
            print("感谢使用，再见！")
            break
        else:
            input("无效的选择，请按回车键重试...")


if __name__ == '__main__':
    # 确保运行所需依赖已安装
    try:
        import pandas
        import jieba
        import sklearn
    except ImportError:
        print("错误：必要的库 (pandas, jieba, scikit-learn) 未安装。")
        print("请运行: pip install pandas jieba scikit-learn")
    else:
        main_menu()
# recommender.py

import pandas as pd
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from db_function import get_db_connection, DATABASE


class MovieRecommender:
    # ... __init__, _load_data_from_db, _chinese_word_cut, _build_model, load_and_build 方法保持不变 ...
    def __init__(self):
        """
        初始化推荐系统，加载数据并构建模型。
        """
        self.db_path = DATABASE
        self.df = None
        self.cosine_sim = None
        self.load_and_build()

    def _load_data_from_db(self):
        """
        从你定义的SQLite数据库加载数据到Pandas DataFrame。
        这里我们复用你的 get_db_connection 上下文管理器。
        """
        print("正在从数据库加载数据...")
        try:
            with get_db_connection() as conn:
                # 使用pandas的read_sql_query可以方便地将查询结果转为DataFrame
                df = pd.read_sql_query("SELECT * FROM movies", conn)

            if df.empty:
                print("警告：数据库中没有数据，推荐功能将不可用。")
                return pd.DataFrame()

            # 将id设为索引，方便后续查找
            df = df.set_index('id')
            print(f"数据加载成功！共 {len(df)} 条电影。")
            return df
        except Exception as e:
            print(f"从数据库加载数据失败: {e}")
            return pd.DataFrame()

    def _chinese_word_cut(self, text):
        """中文分词函数"""
        return " ".join(jieba.cut(text))

    def _build_model(self):
        """构建推荐模型的核心步骤"""
        if self.df is None or self.df.empty:
            return

        print("开始构建推荐模型...")
        # 1. 特征工程：合并类别和评论作为电影的“内容”
        # 给予类别更高的权重（重复3次），使其在相似度计算中更重要
        self.df['content'] = self.df['category'].str.replace('/', ' ') * 3 + ' ' + self.df['comments']

        # 2. 中文分词
        self.df['content_cut'] = self.df['content'].apply(self._chinese_word_cut)

        # 3. TF-IDF向量化
        tfidf_vectorizer = TfidfVectorizer(max_features=5000)
        tfidf_matrix = tfidf_vectorizer.fit_transform(self.df['content_cut'])
        print(f"TF-IDF矩阵构建完成，形状: {tfidf_matrix.shape}")

        # 4. 计算余弦相似度矩阵
        self.cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
        print("余弦相似度矩阵计算完成。")
        print("模型构建完毕！\n")

    def load_and_build(self):
        """封装加载和构建的完整流程"""
        self.df = self._load_data_from_db()
        self._build_model()

    # ---  ↓↓↓  修改这个方法  ↓↓↓  ---
    def get_recommendations(self, partial_title, top_n=5):
        """
        根据给定的电影标题（支持部分匹配），返回最相似的 top_n 部电影。
        """
        if self.df is None or self.df.empty or self.cosine_sim is None:
            return "模型未初始化或数据库为空，无法提供推荐。"

        # 1. 查找部分匹配的电影（忽略大小写）
        # na=False确保标题中的空值不会导致错误
        matching_movies = self.df[self.df['title'].str.contains(partial_title, case=False, na=False)]

        # 2. 处理查找结果
        if matching_movies.empty:
            return f"错误：数据库中未找到任何包含 '{partial_title}' 的电影。"

        chosen_title = None
        movie_index = None

        if len(matching_movies) == 1:
            # 2a. 只有一个匹配项，直接选中
            chosen_title = matching_movies['title'].iloc[0]
            movie_index = matching_movies.index[0]
            print(f"已为您精确匹配到电影: 《{chosen_title}》")
        else:
            # 2b. 有多个匹配项，让用户选择
            print(f"找到多部包含 '{partial_title}' 的电影，请选择一部：")
            for i, title in enumerate(matching_movies['title']):
                print(f"  {i + 1}. {title}")

            while True:
                try:
                    choice_str = input(f"请输入序号 [1-{len(matching_movies)}] (或输入 'q' 取消): ")
                    if choice_str.lower() == 'q':
                        return "操作已取消。"

                    choice_idx = int(choice_str) - 1
                    if 0 <= choice_idx < len(matching_movies):
                        chosen_title = matching_movies['title'].iloc[choice_idx]
                        movie_index = matching_movies.index[choice_idx]
                        break
                    else:
                        print("无效的序号，请重新输入。")
                except ValueError:
                    print("请输入一个有效的数字。")

        # --- 从这里开始，我们已经有了一个确定的 movie_index，后续逻辑不变 ---

        # 3. 找到电影在余弦相似度矩阵中的位置
        matrix_idx = self.df.index.get_loc(movie_index)

        # 4. 获取该电影与其他所有电影的相似度分数
        sim_scores = list(enumerate(self.cosine_sim[matrix_idx]))

        # 5. 根据相似度分数降序排序
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

        # 6. 获取除了自身以外最相似的 top_n 个电影的矩阵索引
        top_movie_indices_in_sim = [i[0] for i in sim_scores[1:top_n + 1]]

        # 7. 通过矩阵索引找到DataFrame中的原始id
        recommended_movie_ids = self.df.iloc[top_movie_indices_in_sim].index

        # 8. 返回推荐电影的详细信息
        return self.df.loc[recommended_movie_ids][['title', 'rating', 'category']]
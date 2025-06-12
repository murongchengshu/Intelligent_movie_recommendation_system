# gui.py
import sys
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QGroupBox, QLabel, QTextEdit, QSpinBox,
                             QTabWidget, QStyle, QSpacerItem, QSizePolicy,QFileDialog)  # 引入新控件
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QIcon  # 引入QIcon


# ... (Worker 和 Stream 类保持不变) ...
# --- 后台工作线程 ---
class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(str)

    def __init__(self, fn, *args,use_progress_callback=False, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.use_progress_callback = use_progress_callback

    @pyqtSlot()
    def run(self):
        # 复制一份kwargs，避免修改原始字典
        local_kwargs = self.kwargs.copy()

        # 如果标记为需要回调，才添加它
        if self.use_progress_callback:
            local_kwargs['progress_callback'] = self.progress.emit

        try:
            # 使用新的局部字典
            result = self.fn(*self.args, **local_kwargs)
            self.result.emit(result)
        except Exception as e:
            self.error.emit((type(e), e, e.__traceback__))
        finally:
            self.finished.emit()


# --- 用于重定向 print 输出到GUI日志窗口的类 ---
class Stream(QObject):
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))

    def flush(self):
        pass  # 在GUI中，flush通常是无操作的


# --- 导入后端逻辑模块 ---
import db_function
import crawler
import csv_import
from recommend import MovieRecommender


# --- 主窗口 ---
class MovieApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能电影推荐系统 ✨-----By zhicheng_tan")
        self.setGeometry(100, 100, 1100, 850)
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

        # 初始化推荐系统实例
        self.recommender = None

        # 应用QSS样式
        self.apply_stylesheet()

        # 创建主控件和布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        # 主布局现在是一个水平布局，左边是操作区，右边是日志区
        self.main_layout = QHBoxLayout(self.central_widget)

        # 创建选项卡控件
        self.tabs = QTabWidget()

        # 创建各个选项卡页面
        self.tab_data = QWidget()
        self.tab_recommend = QWidget()
        self.tab_browse = QWidget()

        self.tabs.addTab(self.tab_data, "数据管理")
        self.tabs.addTab(self.tab_recommend, "智能推荐")
        self.tabs.addTab(self.tab_browse, "浏览数据")

        # 为每个选项卡页面设置布局和内容
        self._create_data_tab()
        self._create_recommend_tab()
        self._create_browse_tab()

        # 创建右侧的日志区域
        self._create_log_area()

        # ---  ↓↓↓  添加状态栏  ↓↓↓  ---
        self.statusBar().showMessage("准备就绪")

        # 将选项卡和日志区添加到主布局
        self.main_layout.addWidget(self.tabs, 7)  # 占据70%宽度
        self.main_layout.addWidget(self.log_group, 3)  # 占据30%宽度

        # --- 线程和信号处理 ---
        self.thread = None
        self.worker = None

        # 重定向print输出到日志窗口
        sys.stdout = Stream(newText=self.log)

        # 启动时在后台加载推荐模型
        self.load_recommender_model()

    def load_recommender_model(self):
        self.log("正在后台加载推荐模型...")
        # ---  ↓↓↓  更新状态栏  ↓↓↓  ---
        self.statusBar().showMessage("正在加载推荐模型，请稍候...")

        self.run_task(MovieRecommender)
        self.worker.result.connect(self.on_recommender_loaded)

    def on_recommender_loaded(self, recommender_instance):
        self.recommender = recommender_instance
        self.log("推荐模型加载完毕！")
        # ---  ↓↓↓  再次更新状态栏，5000毫秒后自动消失  ↓↓↓  ---
        self.statusBar().showMessage("模型加载成功，准备就绪！", 5000)
    def _create_data_tab(self):
        """创建“数据管理”选项卡页面"""
        layout = QVBoxLayout(self.tab_data)

        # 初始化数据库
        init_group = QGroupBox("数据库(用于清空数据库中的数据)")
        init_layout = QHBoxLayout()
        self.init_db_button = QPushButton("初始化/重置数据库")
        self.init_db_button.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.init_db_button.clicked.connect(self.run_init_db)
        init_layout.addWidget(self.init_db_button)
        init_group.setLayout(init_layout)
        db_desc_label = QLabel("<b>作用:</b> 清空并重建数据库。<b>注意:</b> 此操作会删除所有现有电影数据，请谨慎使用。")
        db_desc_label.setWordWrap(True)
        db_desc_label.setStyleSheet("color: #ecf0f1;padding-left: 10px; padding-bottom: 15px;")  # 添加一些内边距

        layout.addWidget(init_group)
        layout.addWidget(db_desc_label)

        # 从CSV导入
        csv_group = QGroupBox("从本地导入")
        csv_layout = QHBoxLayout()
        self.import_csv_button = QPushButton("从 默认top250.csv 导入")
        self.import_csv_button.setIcon(self.style().standardIcon(QStyle.SP_DriveHDIcon))
        self.import_csv_button.clicked.connect(self.run_import_csv)

        # 添加新的、用于选择文件的按钮
        self.import_custom_csv_button = QPushButton("选择自定义 CSV 文件导入...")
        self.import_custom_csv_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.import_custom_csv_button.clicked.connect(self.run_import_custom_csv)  # 连接到新方法

        csv_layout.addWidget(self.import_csv_button)
        csv_layout.addWidget(self.import_custom_csv_button)
        csv_group.setLayout(csv_layout)

        csv_desc_label = QLabel(
            "<b>作用:</b> 从utf-8编码的CSV文件批量导入电影数据。<b>要求:</b> CSV文件需包含 'title ', 'star ', 'all_tags', 'description' 等列。")
        csv_desc_label.setWordWrap(True)
        csv_desc_label.setStyleSheet("color: #ecf0f1;padding-left: 10px; padding-bottom: 15px;")

        layout.addWidget(csv_group)
        layout.addWidget(csv_desc_label)


        # 爬虫
        crawl_group = QGroupBox("从网络爬取")
        crawl_layout = QHBoxLayout()
        crawl_layout.addWidget(QLabel("爬取页数:"))
        self.pages_spinbox = QSpinBox()
        self.pages_spinbox.setMinimum(1)
        self.pages_spinbox.setValue(1)
        self.crawl_button = QPushButton("开始爬取")
        self.crawl_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        self.crawl_button.clicked.connect(self.run_crawl)
        crawl_layout.addWidget(self.pages_spinbox)
        crawl_layout.addWidget(self.crawl_button)
        crawl_group.setLayout(crawl_layout)

        crawl_desc_label = QLabel(
            "<b>作用:</b> 从 hdmoli.pro 网站实时爬取最新的电影信息。<b>提示:</b> 爬取页数越多，耗时越长。")
        crawl_desc_label.setWordWrap(True)
        crawl_desc_label.setStyleSheet("color: #ecf0f1;padding-left: 10px; padding-bottom: 15px;")

        layout.addWidget(crawl_group)
        layout.addWidget(crawl_desc_label)

        layout.addStretch()  # 弹簧
    def _create_recommend_tab(self):
        """创建“智能推荐”选项卡页面"""
        layout = QVBoxLayout(self.tab_recommend)

        input_group = QGroupBox("输入电影")
        input_layout = QHBoxLayout()
        self.movie_input = QLineEdit()
        self.movie_input.setPlaceholderText("输入你喜欢的电影名（支持模糊搜索）")
        self.recommend_button = QPushButton("获取推荐")
        self.recommend_button.setIcon(self.style().standardIcon(QStyle.SP_DialogYesButton))
        self.recommend_button.clicked.connect(self.get_recommendations)
        input_layout.addWidget(self.movie_input)
        input_layout.addWidget(self.recommend_button)
        input_group.setLayout(input_layout)

        result_group = QGroupBox("推荐结果")
        result_layout = QVBoxLayout()
        self.recommend_table = QTableWidget()
        self.setup_table_style(self.recommend_table)
        result_layout.addWidget(self.recommend_table)
        result_group.setLayout(result_layout)

        layout.addWidget(input_group)
        layout.addWidget(result_group)

    def _create_browse_tab(self):
        """创建“浏览数据”选项卡页面"""
        layout = QVBoxLayout(self.tab_browse)

        self.browse_table = QTableWidget()
        self.setup_table_style(self.browse_table)

        self.show_db_button = QPushButton("刷新数据库内容")
        self.show_db_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.show_db_button.clicked.connect(self.show_all_db_content)

        layout.addWidget(self.show_db_button)
        layout.addWidget(self.browse_table)

    def _create_log_area(self):
        """创建右侧的日志区域"""
        self.log_group = QGroupBox("日志")
        layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        self.log_group.setLayout(layout)

    def log(self, message):
        self.log_text.append(message)
        self.log_text.ensureCursorVisible()

    # --- 按钮使能/禁能 ---
    def set_buttons_enabled(self, enabled):
        self.init_db_button.setEnabled(enabled)
        self.import_csv_button.setEnabled(enabled)
        self.import_custom_csv_button.setEnabled(enabled)
        self.crawl_button.setEnabled(enabled)
        self.recommend_button.setEnabled(enabled)
        self.show_db_button.setEnabled(enabled)

    # --- 表格样式和数据填充 ---
    def setup_table_style(self, table):
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["ID", "标题", "评分", "类别"])
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)  # 斑马条纹

    def populate_table(self, table, df):
        if df is None:
            table.setRowCount(0)
            return

        table.setRowCount(df.shape[0])
        table.setColumnCount(df.shape[1])
        table.setHorizontalHeaderLabels([str(col) for col in df.columns])

        for row_idx, row in df.iterrows():
            for col_idx, col_name in enumerate(df.columns):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(row[col_name])))

    # --- QSS 样式 ---
        # gui.py -> class MovieApp

    def apply_stylesheet(self):
            qss = """
                QWidget {
                    font-size: 14px;
                    font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
                }
                QMainWindow {
                    background-color: #2c3e50;
                }
                QGroupBox {
                    background-color: #34495e;
                    color: #ecf0f1;
                    border: 1px solid #2c3e50;
                    border-radius: 5px;
                    margin-top: 1ex;
                    padding-top: 20px; /* 这会将Group内的控件向下推，为标题留出空间 */
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 3px;
                }
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #1a5276;
                }
                QPushButton:disabled {
                    background-color: #95a5a6;
                }
                QLineEdit, QTextEdit, QSpinBox {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    border: 1px solid #34495e;
                    border-radius: 4px;
                    padding: 5px;
                }
                QTabWidget::pane {
                    border: 1px solid #2c3e50;
                }
                QTabBar::tab {
                    background: #34495e;
                    color: #ecf0f1;
                    padding: 10px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #4a627a;
                }
                QTableWidget {
                    background-color: #34495e;
                    color: #ecf0f1;
                    gridline-color: #4a627a;
                    alternate-background-color: #2c3e50;
                }
                QHeaderView::section {
                    background-color: #1abc9c;
                    color: white;
                    padding: 4px;
                    border: 1px solid #16a085;
                }
            """
            self.setStyleSheet(qss)

    # --- 槽函数 (几乎不变，只是更新了正确的表格) ---
    def run_init_db(self):
        db_function.create_movies_table()
        self.log("数据库和 'movies' 表已成功创建/重置。")

    def run_import_csv(self):
        self.log("开始从默认 top250.csv 导入数据 (后台执行)...")
        file_path = './data/top250.csv'
        self.run_task(csv_import.import_from_csv, file_path, use_progress_callback=True)

        # 添加新的槽函数，用于处理自定义CSV导入
    def run_import_custom_csv(self):
        """打开文件对话框让用户选择CSV文件，然后导入"""
        # 打开文件选择对话框
        # 第一个参数是父窗口，第二个是标题，第三个是默认目录，第四个是文件类型过滤器
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择一个CSV文件",
            "",  # 默认目录（空字符串表示上次使用的目录）
            "CSV 文件 (*.csv);;所有文件 (*)"
        )
          # 如果用户选择了文件 (file_path不是空字符串)
        # if file_path:
        self.log(f"用户选择了文件: {file_path}")
        self.run_task(csv_import.import_from_csv, file_path, use_progress_callback=True)
    def run_crawl(self):
        num_pages = self.pages_spinbox.value()
        self.log(f"开始爬取 {num_pages} 页数据 (后台执行)...")
        self.run_task(crawler.pachong, num_pages, use_progress_callback=True)
        self.worker.finished.connect(lambda: self.log("爬取任务完成。"))

    def load_recommender_model(self):
        self.log("正在后台加载推荐模型...")
        self.run_task(MovieRecommender)
        self.worker.result.connect(self.on_recommender_loaded)

    def on_recommender_loaded(self, recommender_instance):
        self.recommender = recommender_instance
        self.log("推荐模型加载完毕！")

    def get_recommendations(self):
        movie_title = self.movie_input.text().strip()
        if not movie_title:
            self.log("请输入电影名称。")
            return
        if not self.recommender:
            self.log("推荐模型尚未加载完成，请稍候。")
            return

        result = self.recommender.get_recommendations(movie_title)

        if isinstance(result, str):
            self.log(result)
        elif isinstance(result, pd.DataFrame):
            self.log(f"为《{movie_title}》找到的推荐结果:")
            # 将结果填充到“推荐”页的表格中
            self.populate_table(self.recommend_table, result.reset_index())

    def show_all_db_content(self):
        self.log("正在从数据库加载所有电影...")
        movies, _ = db_function.get_movies_paginated(1, 10000)
        df = pd.DataFrame(movies, columns=['id', 'title', 'rating', 'category'])
        # 将结果填充到“浏览”页的表格中
        self.populate_table(self.browse_table, df)
        self.log(f"已加载 {len(df)} 条电影。")

    # --- 后台任务处理 (保持不变) ---
    def run_task(self, fn, *args,use_progress_callback=False, **kwargs):
        self.thread = QThread()
        self.worker = Worker(fn, *args, use_progress_callback=use_progress_callback,**kwargs)
        self.worker.moveToThread(self.thread)

        self.worker.progress.connect(self.log)
        self.worker.error.connect(lambda e: self.log(f"错误: {e[1]}"))
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
        self.set_buttons_enabled(False)
        self.worker.finished.connect(lambda: self.set_buttons_enabled(True))


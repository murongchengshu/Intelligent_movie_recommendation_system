# main.py
import sys
from PyQt5.QtWidgets import QApplication
from gui import MovieApp # 从我们新建的 gui.py 中导入主窗口类

if __name__ == '__main__':
    # 检查依赖的代码可以保留，但对于GUI来说，更好的方式是在GUI启动时提示
    try:
        import pandas
        import jieba
        import sklearn
        import requests
        import bs4
    except ImportError as e:
        print(f"错误：缺少必要的库: {e.name}")
        print("请运行: pip install pandas jieba scikit-learn requests beautifulsoup4 lxml PyQt5")
        sys.exit(1) # 退出程序

    # --- 启动GUI应用程序 ---
    app = QApplication(sys.argv)
    window = MovieApp()
    window.show()
    sys.exit(app.exec_())
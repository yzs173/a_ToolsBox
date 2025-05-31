"""
音乐下载工具 - 基于网易云音乐
版本: 1.5
更新内容：
- 优化用户界面，增加下载进度显示
- 美化界面，增加阴影和圆角效果
- 增加错误处理和日志功能
"""
import sys
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QProgressBar, QFileDialog, QMessageBox, QListWidgetItem
)
import requests

# 配置项
TOOL_NAME = "音乐下载器"
DESCRIPTION = "从网易云音乐下载歌曲"

# 请求头信息
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.3741.400 QQBrowser/10.5.3863.400"
}

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("music_download.log"), logging.StreamHandler()]
)

class ToolWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("音乐下载器")
        self.setMinimumSize(800, 600)
        self.download_path = os.getcwd()  # 默认下载路径为当前目录
        self.return_to_toolbox = None  # 返回工具箱的函数
        self.thread_pool = ThreadPoolExecutor(max_workers=5)  # 线程池
        self._setup_ui()

    def _setup_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()

        # 搜索框和按钮
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入歌曲名称")
        self.search_input.setStyleSheet("padding: 8px; border-radius: 4px; border: 1px solid #ccc;")
        self.search_input.returnPressed.connect(self._search_songs)
        search_button = QPushButton("搜索")
        search_button.setStyleSheet("padding: 8px 16px; border-radius: 4px; background: #007bff; color: white;")
        search_button.clicked.connect(self._search_songs)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)

        # 搜索结果列表
        self.song_list = QListWidget()
        self.song_list.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; padding: 8px;")
        self.song_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)  # 支持多选
        self.song_list.itemSelectionChanged.connect(self._update_download_button)

        # 下载路径选择
        path_layout = QHBoxLayout()
        self.path_label = QLabel(f"下载路径: {self.download_path}")
        path_button = QPushButton("选择路径")
        path_button.setStyleSheet("padding: 8px 16px; border-radius: 4px; background: #28a745; color: white;")
        path_button.clicked.connect(self._select_download_path)
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(path_button)

        # 下载按钮
        self.download_button = QPushButton("下载选中歌曲")
        self.download_button.setStyleSheet("padding: 8px 16px; border-radius: 4px; background: #dc3545; color: white;")
        self.download_button.setEnabled(False)  # 默认禁用
        self.download_button.clicked.connect(self._download_selected_songs)

        # 返回按钮
        return_button = QPushButton("返回工具箱")
        return_button.setStyleSheet("padding: 8px 16px; border-radius: 4px; background: #6c757d; color: white;")
        return_button.clicked.connect(self._return_to_toolbox)

        # 布局
        layout.addLayout(search_layout)
        layout.addWidget(QLabel("搜索结果:"))
        layout.addWidget(self.song_list)
        layout.addLayout(path_layout)
        layout.addWidget(self.download_button)
        layout.addWidget(return_button)
        self.setLayout(layout)

    def _search_songs(self):
        """搜索歌曲"""
        keyword = self.search_input.text()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入歌曲名称！")
            return

        self.song_list.clear()
        try:
            search_url = f'https://music.163.com/api/search/get/web?csrf_token=hlpretag=&hlposttag=&s={keyword}&type=1&offset=0&total=true&limit=10'
            response = requests.get(url=search_url, headers=HEADERS).json()
            songs = response['result']['songs']
            for song in songs:
                name = song['name']
                author = song['artists'][0]['name']
                song_id = song['id']
                self.song_list.addItem(f"{name} - {author} (ID: {song_id})")
        except Exception as e:
            logging.error(f"搜索失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"搜索失败: {str(e)}")

    def _select_download_path(self):
        """选择下载路径"""
        path = QFileDialog.getExistingDirectory(self, "选择下载路径", self.download_path)
        if path:
            self.download_path = path
            self.path_label.setText(f"下载路径: {self.download_path}")

    def _update_download_button(self):
        """更新下载按钮状态"""
        self.download_button.setEnabled(len(self.song_list.selectedItems()) > 0)

    def _download_selected_songs(self):
        """下载选中的歌曲"""
        selected_items = self.song_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要下载的歌曲！")
            return

        for item in selected_items:
            song_info = item.text()
            song_id = song_info.split("(ID: ")[1].rstrip(")")
            song_name = song_info.split(" - ")[0]
            self.thread_pool.submit(self._download_task, song_id, song_name)

    def _download_task(self, song_id, song_name):
        """下载任务"""
        url = f'http://music.163.com/song/media/outer/url?id={song_id}'
        try:
            response = requests.get(url=url, headers=HEADERS, stream=True)
            file_path = os.path.join(self.download_path, f"{song_name}.mp3")
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"{song_name} 下载完成")
            self.song_list.addItem(f"{song_name} 下载完成")
        except Exception as e:
            logging.error(f"{song_name} 下载失败: {str(e)}")
            self.song_list.addItem(f"{song_name} 下载失败: {str(e)}")

    def _return_to_toolbox(self):
        """返回工具箱"""
        if self.return_to_toolbox:
            self.return_to_toolbox()

    def closeEvent(self, event):
        """关闭窗口时清理资源"""
        self.thread_pool.shutdown(wait=False)
        super().closeEvent(event)
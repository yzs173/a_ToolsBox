import os
import re
import subprocess
import requests
from lxml import html
import traceback
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QProgressBar, QRadioButton, 
    QButtonGroup, QTextEdit
)
import sys
import you_get
TOOL_NAME = "B站视频下载器"
DESCRIPTION = "下载B站视频（需要配置环境）"
class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, int, int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url, output_dir, download_type):
        super().__init__()
        self.url = url
        self.output_dir = os.path.abspath(output_dir)
        self.download_type = download_type
        self.video_urls = []

    def run(self):
        try:
            self.video_urls = [self.url]

            total = len(self.video_urls)
            for idx, video_url in enumerate(self.video_urls):
                self._download_single(video_url, idx+1, total)

            self.finished_signal.emit(True, "下载完成！")
        except Exception as e:
            self.finished_signal.emit(False, f"下载失败: {str(e)}\n{traceback.format_exc()}")

    def _download_single(self, url, current, total):
        if self.download_type == "collection":


            # 1. 发送请求获取网页内容
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 检查请求是否成功

            # 2. 解析 HTML
            tree = html.fromstring(response.content)

            # 3. 使用 XPath 定位所有带 data-key 的元素
            elements = tree.xpath("/html/body/div[2]/div[2]/div[2]/div//*[@data-key]")

            # 4. 按顺序提取 data-key 的值
            data_keys = [element.get("data-key") for element in elements]
            if data_keys[0][0] == 'B':
                # 设置列表
                for idx, key in enumerate(data_keys, 1):
                    data_keys[idx-1] = 'https://www.bilibili.com/video/' + key
                for url_used in data_keys:            
                    cmd = [
                        "you-get",
                        "--playlist",
                        "--no-caption",
                        "-o", self.output_dir+"",
                        "--debug",
                        # "-c",cookies,
                        # "-l",
                        url_used
                    ]
                    self.log_signal.emit(f"执行命令: {' '.join(cmd)}")

                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        bufsize=1,
                        universal_newlines=True,
                        encoding='utf-8',
                        errors='replace'
                    )

                    while True:
                        output = process.stdout.readline()
                        if not output and process.poll() is not None:
                            break
                        if output:
                            self.log_signal.emit(output.strip())
                            if "Downloading" in output:
                                if match := re.search(r'(\d+\.\d+)%', output):
                                    percent = float(match.group(1))
                                    self.progress_signal.emit(current, total, int(percent))
                            elif "100%" in output:
                                self.progress_signal.emit(current, total, 100)

                    if process.returncode != 0:
                        raise Exception(f"下载失败，退出码: {process.returncode}")
            else:
                cmd = [
                    "you-get",
                    "--no-caption",
                    "-o", self.output_dir+"",
                    "--debug",
                    "-l",          
                    url
                ]
                
                self.log_signal.emit(f"执行命令: {' '.join(cmd)}")

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace'
                )

                while True:
                    output = process.stdout.readline()
                    if not output and process.poll() is not None:
                        break
                    if output:
                        self.log_signal.emit(output.strip())
                        if "Downloading" in output:
                            if match := re.search(r'(\d+\.\d+)%', output):
                                percent = float(match.group(1))
                                self.progress_signal.emit(current, total, int(percent))
                        elif "100%" in output:
                            self.progress_signal.emit(current, total, 100)

                if process.returncode != 0:
                    raise Exception(f"下载失败，退出码: {process.returncode}")

        else:
            cmd = [
                "you-get",
                "--no-caption",
                "-o", self.output_dir+"",
                "--debug",          
                url
            ]
            
            self.log_signal.emit(f"执行命令: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )

            while True:
                output = process.stdout.readline()
                if not output and process.poll() is not None:
                    break
                if output:
                    self.log_signal.emit(output.strip())
                    if "Downloading" in output:
                        if match := re.search(r'(\d+\.\d+)%', output):
                            percent = float(match.group(1))
                            self.progress_signal.emit(current, total, int(percent))
                    elif "100%" in output:
                        self.progress_signal.emit(current, total, 100)

            if process.returncode != 0:
                raise Exception(f"下载失败，退出码: {process.returncode}")

class BilibiliDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("B站视频下载器")
        self.setMinimumSize(800, 600)
        self.output_dir = os.path.expanduser("~\Downloads")
        self._setup_ui()
        # self._check_dependencies()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # 下载类型选择
        type_group = QButtonGroup(self)
        self.single_radio = QRadioButton("单个视频")
        self.collection_radio = QRadioButton("视频合集")
        type_group.addButton(self.single_radio)
        type_group.addButton(self.collection_radio)
        self.single_radio.setChecked(True)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("下载类型:"))
        type_layout.addWidget(self.single_radio)
        type_layout.addWidget(self.collection_radio)
        type_layout.addStretch()

        # URL输入
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入B站视频链接（示例：https://www.bilibili.com/video/BV1xx411c7XX）")
        self.url_input.setStyleSheet("padding:8px; font-size:14px;")

        # 路径选择
        self.path_label = QLabel(f"保存路径: {self.output_dir}")
        path_btn = QPushButton("更改路径", clicked=self._select_path)
        path_btn.setStyleSheet("padding:6px 12px; background:#4CAF50; color:black;")

        # 控制按钮
        self.download_btn = QPushButton("开始下载", clicked=self._start_download)
        self.download_btn.setStyleSheet("padding:12px 24px; background:#2196F3; color:black; font-size:16px;")

        # 进度条
        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress.setVisible(False)
        # 返回按钮
        return_button = QPushButton("返回工具箱")
        return_button.setStyleSheet("padding: 8px 16px; border-radius: 4px; background: #6c757d; color: white;")
        return_button.clicked.connect(self._return_to_toolbox)

        # 日志框
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            font-family: Consolas; 
            font-size: 12px; 
            background-color: #1E1E1E; 
            color: #D4D4D4;
            padding: 10px;
        """)

        # 布局组装
        layout.addLayout(type_layout)
        layout.addWidget(QLabel("视频链接:"))
        layout.addWidget(self.url_input)
        layout.addWidget(self.path_label)
        layout.addWidget(path_btn)
        layout.addWidget(self.download_btn)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("操作日志:"))
        layout.addWidget(self.log_view)
        layout.addWidget(return_button)

        self.setLayout(layout)

    def _check_dependencies(self):
        missing = []
        for cmd in ["you-get", "ffmpeg"]:
            try:
                result = subprocess.run([cmd, "--version"], check=True, capture_output=True, text=True)
                self.log_view.append(f"[检查] {cmd} 版本: {result.stdout.splitlines()[0]}")
            except Exception as e:
                missing.append(f"{cmd} ({e})")
                self.log_view.append(f"[错误] 找不到依赖: {cmd}")

        if missing:
            QMessageBox.critical(
                self, 
                "缺少必要依赖", 
                f"缺失组件: {', '.join(missing)}\n\n"
                "解决方案：\n"
                "1. 安装you-get: pip install -U you-get\n"
                "2. 安装ffmpeg\n"
                "   Windows: 从官网下载并添加至PATH\n"
                "   macOS: brew install ffmpeg\n"
                "   Linux: sudo apt-get install ffmpeg"
            )
            sys.exit(1)

    def _select_path(self):
        if path := QFileDialog.getExistingDirectory(self, "选择保存路径"):
            self.output_dir = os.path.abspath(path)
            self.path_label.setText(f"保存路径: {self.output_dir}")
            self.log_view.append(f"[配置] 保存路径已更改为: {self.output_dir}")

    def _start_download(self):
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.download_btn.setEnabled(False)
        self.log_view.clear()

        url = self.url_input.text().strip()
        if not re.match(r"^https?://(www\.)?bilibili\.com/video/", url):
            QMessageBox.warning(self, "输入错误", "请输入有效的B站视频链接（以https://www.bilibili.com/video/开头）")
            self.download_btn.setEnabled(True)
            return

        download_type = "collection" if self.collection_radio.isChecked() else "video"
        self.worker = DownloadThread(url, self.output_dir, download_type)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.log_signal.connect(self.log_view.append)
        self.worker.finished_signal.connect(self._handle_result)
        self.worker.start()

    def _update_progress(self, current, total, percent):
        self.progress.setValue(percent)
        self.progress.setFormat(f"下载进度 ({current}/{total}) - {percent}%")

    def _handle_result(self, success, message):
        self.progress.setVisible(False)
        self.download_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.log_view.append("[成功] 下载已完成，请检查保存路径")
        else:
            error_msg = f"[严重错误] {message}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_view.append(error_msg)
    def _return_to_toolbox(self):
        """返回工具箱"""
        if self.return_to_toolbox:
            self.return_to_toolbox()
class ToolWindow(BilibiliDownloader):
    def __init__(self, parent=None):
        super().__init__()
        self.return_to_toolbox = None  # 返回工具箱的函数

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BilibiliDownloader()
    window.show()
    sys.exit(app.exec())

import os
import sys
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QProgressBar, QListWidget,
    QMessageBox
)
import subprocess
TOOL_NAME = "视频转换器"
DESCRIPTION = "视频转化为音频"
class AudioConverter(QThread):
    progress = pyqtSignal(int, str)  # 进度百分比，当前文件名
    finished = pyqtSignal(bool, str)  # 完成状态，最终消息

    def __init__(self, input_paths, output_dir):
        super().__init__()
        self.input_paths = input_paths
        self.output_dir = output_dir
        self.total_files = len(input_paths)
        self.processed_files = 0

    def run(self):
        try:
            for index, input_path in enumerate(self.input_paths):
                if not os.path.exists(input_path):
                    continue
                
                # 更新进度
                self.processed_files = index + 1
                filename = os.path.basename(input_path)
                self.progress.emit(
                    int((self.processed_files / self.total_files) * 100),
                    f"正在转换: {filename}"
                )
                
                # 生成输出路径
                output_name = os.path.splitext(filename)[0] + ".mp3"
                output_path = os.path.join(self.output_dir, output_name)
                
                # 使用FFmpeg转换
                command = [
                    "ffmpeg",
                    "-i", input_path,
                    "-vn",          # 禁用视频流
                    "-acodec", "libmp3lame",  # 使用MP3编码
                    "-q:a", "2",    # 音频质量（0-9，0为最高质量）
                    "-y",           # 覆盖输出文件
                    output_path
                ]
                subprocess.run(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
            
            self.finished.emit(True, f"成功转换 {self.processed_files}/{self.total_files} 个文件")
        except Exception as e:
            self.finished.emit(False, f"转换失败: {str(e)}")

class VideoToAudioTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频转音频工具")
        self.setMinimumSize(800, 500)
        self.input_files = []
        self.output_dir = os.path.expanduser("~/Desktop")  # 默认输出到桌面
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # 文件选择区域
        file_controls = QHBoxLayout()
        self.btn_add_files = QPushButton("添加文件")
        self.btn_add_files.setStyleSheet("padding: 8px; background: #4CAF50; color: white;")
        self.btn_add_files.clicked.connect(self._add_files)
        
        self.btn_add_folder = QPushButton("添加文件夹")
        self.btn_add_folder.setStyleSheet("padding: 8px; background: #2196F3; color: white;")
        self.btn_add_folder.clicked.connect(self._add_folder)
        
        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.setStyleSheet("padding: 8px; background: #f44336; color: white;")
        self.btn_clear.clicked.connect(self._clear_list)
        
        file_controls.addWidget(self.btn_add_files)
        file_controls.addWidget(self.btn_add_folder)
        file_controls.addWidget(self.btn_clear)

        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 10px;
            }
            QListWidget::item {
                padding: 5px;
            }
        """)

        # 输出路径选择
        output_controls = QHBoxLayout()
        self.lbl_output = QLabel(f"输出目录: {self.output_dir}")
        self.btn_choose_output = QPushButton("更改目录")
        self.btn_choose_output.setStyleSheet("padding: 8px; background: #9C27B0; color: white;")
        self.btn_choose_output.clicked.connect(self._choose_output_dir)
        output_controls.addWidget(self.lbl_output)
        output_controls.addWidget(self.btn_choose_output)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 操作按钮
        self.btn_convert = QPushButton("开始转换")
        self.btn_convert.setStyleSheet("""
            QPushButton {
                padding: 12px;
                background: #FF9800;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background: #BDBDBD;
            }
        """)
        self.btn_convert.clicked.connect(self._start_conversion)
        # 返回按钮
        return_button = QPushButton("返回工具箱")
        return_button.setStyleSheet("padding: 8px 16px; border-radius: 4px; background: #6c757d; color: white;")
        return_button.clicked.connect(self._return_to_toolbox)

        # 布局
        layout.addLayout(file_controls)
        layout.addWidget(self.file_list)
        layout.addLayout(output_controls)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.btn_convert)
        layout.addWidget(return_button)
        self.setLayout(layout)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.flv)"
        )
        if files:
            self.input_files.extend(files)
            self.file_list.addItems([os.path.basename(f) for f in files])

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择包含视频的文件夹")
        if folder:
            valid_ext = {'.mp4', '.avi', '.mkv', '.mov', '.flv'}
            for root, _, files in os.walk(folder):
                for file in files:
                    if os.path.splitext(file)[1].lower() in valid_ext:
                        path = os.path.join(root, file)
                        self.input_files.append(path)
                        self.file_list.addItem(file)

    def _clear_list(self):
        self.input_files.clear()
        self.file_list.clear()
        self.progress_bar.reset()

    def _choose_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_dir = path
            self.lbl_output.setText(f"输出目录: {path}")

    def _start_conversion(self):
        if not self.input_files:
            QMessageBox.warning(self, "警告", "请先添加要转换的视频文件！")
            return
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 禁用界面控件
        self._set_ui_enabled(False)
        
        # 启动转换线程
        self.converter = AudioConverter(self.input_files, self.output_dir)
        self.converter.progress.connect(self._update_progress)
        self.converter.finished.connect(self._conversion_finished)
        self.converter.start()

    def _update_progress(self, percent, filename):
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"{filename} ({percent}%)")

    def _conversion_finished(self, success, message):
        self._set_ui_enabled(True)
        self.progress_bar.setValue(100 if success else 0)
        QMessageBox.information(self, "完成" if success else "错误", message)

    def _set_ui_enabled(self, enabled):
        self.btn_add_files.setEnabled(enabled)
        self.btn_add_folder.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
        self.btn_choose_output.setEnabled(enabled)
        self.btn_convert.setEnabled(enabled)
    def _return_to_toolbox(self):
        """返回工具箱"""
        if self.return_to_toolbox:
            self.return_to_toolbox()
class ToolWindow(VideoToAudioTool):
    def __init__(self, parent=None):
        super().__init__()
        self.return_to_toolbox = None  # 返回工具箱的函数
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoToAudioTool()
    window.show()
    sys.exit(app.exec())
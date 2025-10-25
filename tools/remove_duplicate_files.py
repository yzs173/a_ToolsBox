import os
import sys
import shutil
from collections import defaultdict
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QFileDialog, QMessageBox, QGroupBox,
    QProgressBar, QCheckBox
)
from PyQt6.QtGui import QIcon

TOOL_NAME = "重复文件清理工具"
DESCRIPTION = "比较两个文件夹中的重复文件（包括子文件夹），并生成去重后的新文件夹"

class DuplicateFileCleaner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("重复文件清理工具")
        self.setMinimumSize(800, 700)
        self.folder_a_path = None  # 文件夹A路径
        self.folder_b_path = None  # 文件夹B路径
        self.output_folder_path = None  # 输出文件夹路径
        self.duplicate_files = []  # 重复文件列表
        self.all_files_a = []  # 文件夹A中的所有文件（包括子文件夹）
        self.all_files_b = []  # 文件夹B中的所有文件（包括子文件夹）
        self._setup_ui()

    def _setup_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()

        # 文件夹A选择
        folder_a_layout = QHBoxLayout()
        self.folder_a_label = QLabel("未选择文件夹A")
        self.folder_a_label.setStyleSheet("font-size: 14px; color: #333;")
        select_folder_a_button = QPushButton("选择文件夹A")
        select_folder_a_button.setStyleSheet("padding: 8px 16px; background: #007bff; color: white; border-radius: 4px;")
        select_folder_a_button.clicked.connect(lambda: self._select_folder("A"))
        
        folder_a_layout.addWidget(self.folder_a_label)
        folder_a_layout.addWidget(select_folder_a_button)

        # 文件夹B选择
        folder_b_layout = QHBoxLayout()
        self.folder_b_label = QLabel("未选择文件夹B")
        self.folder_b_label.setStyleSheet("font-size: 14px; color: #333;")
        select_folder_b_button = QPushButton("选择文件夹B")
        select_folder_b_button.setStyleSheet("padding: 8px 16px; background: #007bff; color: white; border-radius: 4px;")
        select_folder_b_button.clicked.connect(lambda: self._select_folder("B"))
        
        folder_b_layout.addWidget(self.folder_b_label)
        folder_b_layout.addWidget(select_folder_b_button)

        # 输出文件夹选择
        output_layout = QHBoxLayout()
        self.output_folder_label = QLabel("未选择输出文件夹")
        self.output_folder_label.setStyleSheet("font-size: 14px; color: #333;")
        select_output_button = QPushButton("选择输出文件夹")
        select_output_button.setStyleSheet("padding: 8px 16px; background: #28a745; color: white; border-radius: 4px;")
        select_output_button.clicked.connect(self._select_output_folder)
        
        output_layout.addWidget(self.output_folder_label)
        output_layout.addWidget(select_output_button)

        # 比较选项
        options_group = QGroupBox("比较选项")
        options_layout = QVBoxLayout()
        
        self.include_subfolders_checkbox = QCheckBox("包含子文件夹中的文件")
        self.include_subfolders_checkbox.setChecked(True)
        
        options_layout.addWidget(self.include_subfolders_checkbox)
        options_group.setLayout(options_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        # 比较按钮
        compare_button = QPushButton("比较文件夹")
        compare_button.setStyleSheet("padding: 8px 16px; background: #ffc107; color: black; border-radius: 4px;")
        compare_button.clicked.connect(self._compare_folders)

        # 重复文件列表
        self.duplicate_list_widget = QListWidget()
        self.duplicate_list_widget.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; padding: 8px;")
        
        # 统计信息
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-size: 14px; color: #333;")

        # 执行清理按钮
        clean_button = QPushButton("生成去重文件夹")
        clean_button.setStyleSheet("padding: 8px 16px; background: #dc3545; color: white; border-radius: 4px;")
        clean_button.clicked.connect(self._generate_clean_folder)

        # 返回按钮
        return_button = QPushButton("返回工具箱")
        return_button.setStyleSheet("padding: 8px 16px; border-radius: 4px; background: #6c757d; color: white;")
        return_button.clicked.connect(self._return_to_toolbox)

        # 布局
        layout.addLayout(folder_a_layout)
        layout.addLayout(folder_b_layout)
        layout.addLayout(output_layout)
        layout.addWidget(options_group)
        layout.addWidget(self.progress_bar)
        layout.addWidget(compare_button)
        layout.addWidget(QLabel("重复文件列表:"))
        layout.addWidget(self.duplicate_list_widget)
        layout.addWidget(self.stats_label)
        layout.addWidget(clean_button)
        layout.addWidget(return_button)
        self.setLayout(layout)

    def _select_folder(self, folder_type):
        """选择文件夹A或B"""
        folder_path = QFileDialog.getExistingDirectory(self, f"选择文件夹{folder_type}")
        if folder_path:
            if folder_type == "A":
                self.folder_a_path = folder_path
                self.folder_a_label.setText(f"文件夹A: {folder_path}")
            else:
                self.folder_b_path = folder_path
                self.folder_b_label.setText(f"文件夹B: {folder_path}")

    def _select_output_folder(self):
        """选择输出文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder_path:
            self.output_folder_path = folder_path
            self.output_folder_label.setText(f"输出文件夹: {folder_path}")

    def _get_all_files(self, folder_path, include_subfolders=True):
        """递归获取文件夹中的所有文件（包括子文件夹）"""
        all_files = []
        
        if not folder_path or not os.path.exists(folder_path):
            return all_files
        
        if include_subfolders:
            # 递归获取所有文件
            for root, dirs, files in os.walk(folder_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    # 计算相对路径，用于显示和比较
                    relative_path = os.path.relpath(file_path, folder_path)
                    all_files.append({
                        'name': file_name,
                        'full_path': file_path,
                        'relative_path': relative_path
                    })
        else:
            # 只获取根目录文件
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):
                    all_files.append({
                        'name': file_name,
                        'full_path': file_path,
                        'relative_path': file_name
                    })
        
        return all_files

    def _compare_folders(self):
        """比较两个文件夹，找出重复文件"""
        if not self.folder_a_path or not self.folder_b_path:
            QMessageBox.warning(self, "提示", "请先选择文件夹A和文件夹B！")
            return

        # 重置状态
        self.duplicate_list_widget.clear()
        self.duplicate_files = []
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # 获取所有文件（包括子文件夹）
        include_subfolders = self.include_subfolders_checkbox.isChecked()
        self.all_files_a = self._get_all_files(self.folder_a_path, include_subfolders)
        self.all_files_b = self._get_all_files(self.folder_b_path, include_subfolders)
        
        total_files = len(self.all_files_a) + len(self.all_files_b)
        if total_files == 0:
            QMessageBox.warning(self, "提示", "选择的文件夹中没有文件！")
            self.progress_bar.setVisible(False)
            return

        # 只通过文件名比较重复文件
        self._compare_by_name()

        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)

    def _compare_by_name(self):
        """通过文件名比较重复文件"""
        # 构建文件名到文件列表的映射
        name_to_files_a = defaultdict(list)
        name_to_files_b = defaultdict(list)
        
        for file_info in self.all_files_a:
            name_to_files_a[file_info['name']].append(file_info)
            
        for file_info in self.all_files_b:
            name_to_files_b[file_info['name']].append(file_info)
        
        # 找出重复的文件名
        common_names = set(name_to_files_a.keys()) & set(name_to_files_b.keys())
        
        for name in common_names:
            # 对于每个重复的文件名，记录所有匹配的文件对
            files_a = name_to_files_a[name]
            files_b = name_to_files_b[name]
            
            # 记录所有重复文件对
            for file_a in files_a:
                for file_b in files_b:
                    self.duplicate_files.append({
                        'name': name,
                        'path_a': file_a['full_path'],
                        'path_b': file_b['full_path'],
                        'relative_a': file_a['relative_path'],
                        'relative_b': file_b['relative_path'],
                        'duplicate_type': '文件名重复'
                    })
                    
                    display_text = f"📄 {name}\n  A: {file_a['relative_path']}\n  B: {file_b['relative_path']}"
                    self.duplicate_list_widget.addItem(display_text)

        # 更新统计信息
        self._update_stats(len(self.all_files_a), len(self.all_files_b), len(self.duplicate_files))

    def _update_stats(self, count_a, count_b, duplicate_count):
        """更新统计信息"""
        # 计算不重复的文件数量
        duplicate_names = set()
        for dup in self.duplicate_files:
            duplicate_names.add(dup['name'])
        
        # 计算不重复的文件数量
        unique_files_a = [f for f in self.all_files_a if f['name'] not in duplicate_names]
        unique_files_b = [f for f in self.all_files_b if f['name'] not in duplicate_names]
        total_unique = len(unique_files_a) + len(unique_files_b)
        
        if count_a + count_b > 0:
            deduplication_rate = len(duplicate_names) / (count_a + count_b) * 100
        else:
            deduplication_rate = 0
            
        stats_text = f"""
        <b>统计信息:</b><br>
        文件夹A: {count_a} 个文件<br>
        文件夹B: {count_b} 个文件<br>
        重复文件: {len(duplicate_names)} 个<br>
        唯一文件: {total_unique} 个<br>
        去重率: {deduplication_rate:.1f}% (删除 {len(duplicate_names)} 个重复文件)
        """
        self.stats_label.setText(stats_text)

    def _generate_clean_folder(self):
        """生成去重后的文件夹"""
        if not self.output_folder_path:
            QMessageBox.warning(self, "提示", "请先选择输出文件夹！")
            return

        if not self.folder_a_path or not self.folder_b_path:
            QMessageBox.warning(self, "提示", "请先选择文件夹A和文件夹B！")
            return

        try:
            # 创建输出文件夹
            output_dir = os.path.join(self.output_folder_path, "去重结果")
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(output_dir)

            # 获取所有重复文件的名称
            duplicate_names = set()
            for dup in self.duplicate_files:
                duplicate_names.add(dup['name'])

            # 复制文件夹A中的不重复文件（保持目录结构）
            files_copied = 0
            
            for file_info in self.all_files_a:
                if file_info['name'] not in duplicate_names:
                    src_path = file_info['full_path']
                    dst_path = os.path.join(output_dir, "文件夹A", file_info['relative_path'])
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    shutil.copy2(src_path, dst_path)
                    files_copied += 1

            # 复制文件夹B中的不重复文件（保持目录结构）
            for file_info in self.all_files_b:
                if file_info['name'] not in duplicate_names:
                    src_path = file_info['full_path']
                    dst_path = os.path.join(output_dir, "文件夹B", file_info['relative_path'])
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    shutil.copy2(src_path, dst_path)
                    files_copied += 1

            QMessageBox.information(self, "成功", 
                f"去重文件夹已生成！\n"
                f"位置: {output_dir}\n"
                f"共保存 {files_copied} 个不重复文件\n"
                f"已删除 {len(duplicate_names)} 个重复文件")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成去重文件夹失败: {str(e)}")

    def _return_to_toolbox(self):
        """返回工具箱"""
        if hasattr(self, 'return_to_toolbox') and self.return_to_toolbox:
            self.return_to_toolbox()


class ToolWindow(DuplicateFileCleaner):
    def __init__(self, parent=None):
        super().__init__()
        self.return_to_toolbox = None  # 返回工具箱的函数


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DuplicateFileCleaner()
    window.show()
    sys.exit(app.exec())
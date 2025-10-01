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
        self.setMinimumSize(800,600)
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
        
        self.name_only_checkbox = QCheckBox("仅比较文件名（不比较文件内容）")
        self.name_only_checkbox.setChecked(True)
        
        self.prefer_a_checkbox = QCheckBox("保留文件夹A中的文件（当文件名重复时）")
        self.prefer_a_checkbox.setChecked(True)
        
        self.include_subfolders_checkbox = QCheckBox("包含子文件夹中的文件")
        self.include_subfolders_checkbox.setChecked(True)
        
        options_layout.addWidget(self.name_only_checkbox)
        options_layout.addWidget(self.prefer_a_checkbox)
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

    def _calculate_file_hash(self, file_path):
        """计算文件的MD5哈希值"""
        import hashlib
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"计算文件哈希失败: {str(e)}")
            return None

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

        # 仅比较文件名
        if self.name_only_checkbox.isChecked():
            self._compare_by_name()
        else:
            self._compare_by_content()

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
            
            # 简单处理：只记录第一对重复文件
            # 实际应用中可能需要更复杂的匹配逻辑
            file_a = files_a[0]
            file_b = files_b[0]
            
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
        self._update_stats(len(self.all_files_a), len(self.all_files_b), len(common_names))

    def _compare_by_content(self):
        """通过文件内容比较重复文件"""
        # 构建文件哈希映射
        file_hashes = defaultdict(list)
        processed_files = 0
        total_files = len(self.all_files_a) + len(self.all_files_b)
        
        # 处理文件夹A中的文件
        for file_info in self.all_files_a:
            file_hash = self._calculate_file_hash(file_info['full_path'])
            if file_hash:
                file_hashes[file_hash].append(('A', file_info))
            processed_files += 1
            self.progress_bar.setValue(int(processed_files / total_files * 50))
        
        # 处理文件夹B中的文件
        for file_info in self.all_files_b:
            file_hash = self._calculate_file_hash(file_info['full_path'])
            if file_hash:
                file_hashes[file_hash].append(('B', file_info))
            processed_files += 1
            self.progress_bar.setValue(50 + int(processed_files / total_files * 50))
        
        # 找出重复文件
        content_duplicates = 0
        for file_hash, file_list in file_hashes.items():
            if len(file_list) > 1:
                # 检查是否来自不同的文件夹
                folders = set(item[0] for item in file_list)
                if len(folders) > 1:
                    content_duplicates += 1
                    # 只记录一个重复对
                    file_a = next((item for item in file_list if item[0] == 'A'), None)
                    file_b = next((item for item in file_list if item[0] == 'B'), None)
                    
                    if file_a and file_b:
                        file_a_info = file_a[1]
                        file_b_info = file_b[1]
                        
                        self.duplicate_files.append({
                            'name': f"{file_a_info['name']} / {file_b_info['name']}",
                            'path_a': file_a_info['full_path'],
                            'path_b': file_b_info['full_path'],
                            'relative_a': file_a_info['relative_path'],
                            'relative_b': file_b_info['relative_path'],
                            'duplicate_type': '内容重复'
                        })
                        
                        display_text = f"🔍 {file_a_info['name']} ↔ {file_b_info['name']}\n  A: {file_a_info['relative_path']}\n  B: {file_b_info['relative_path']}"
                        self.duplicate_list_widget.addItem(display_text)

        # 更新统计信息
        self._update_stats(len(self.all_files_a), len(self.all_files_b), content_duplicates)

    def _update_stats(self, count_a, count_b, duplicate_count):
        """更新统计信息"""
        total_files = count_a + count_b
        unique_files = total_files - duplicate_count
        
        if total_files > 0:
            deduplication_rate = duplicate_count / total_files * 100
        else:
            deduplication_rate = 0
            
        stats_text = f"""
        <b>统计信息:</b><br>
        文件夹A: {count_a} 个文件<br>
        文件夹B: {count_b} 个文件<br>
        重复文件: {duplicate_count} 个<br>
        唯一文件: {unique_files} 个<br>
        去重率: {deduplication_rate:.1f}% (删除 {duplicate_count} 个重复文件)
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

            # 复制文件夹A中的所有文件（保持目录结构）
            files_copied = 0
            prefer_a = self.prefer_a_checkbox.isChecked()
            
            for file_info in self.all_files_a:
                src_path = file_info['full_path']
                dst_path = os.path.join(output_dir, file_info['relative_path'])
                
                # 确保目标目录存在
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                
                # 检查是否重复
                is_duplicate = any(
                    file_info['name'] == dup['name'] or 
                    file_info['full_path'] == dup['path_a'] or 
                    file_info['full_path'] == dup['path_b']
                    for dup in self.duplicate_files
                )
                
                if not is_duplicate or prefer_a:
                    shutil.copy2(src_path, dst_path)
                    files_copied += 1

            # 复制文件夹B中的非重复文件（保持目录结构）
            for file_info in self.all_files_b:
                src_path = file_info['full_path']
                dst_path = os.path.join(output_dir, file_info['relative_path'])
                
                # 确保目标目录存在
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                
                # 检查是否重复
                is_duplicate = any(
                    file_info['name'] == dup['name'] or 
                    file_info['full_path'] == dup['path_a'] or 
                    file_info['full_path'] == dup['path_b']
                    for dup in self.duplicate_files
                )
                
                if not is_duplicate:
                    shutil.copy2(src_path, dst_path)
                    files_copied += 1
                elif not prefer_a:
                    # 重复文件但优先保留B文件夹的版本
                    shutil.copy2(src_path, dst_path)
                    # 因为覆盖了A文件夹的文件，所以总数不变

            QMessageBox.information(self, "成功", 
                f"去重文件夹已生成！\n"
                f"位置: {output_dir}\n"
                f"共保存 {files_copied} 个文件\n"
                f"已删除 {len(self.duplicate_files)} 个重复文件")

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
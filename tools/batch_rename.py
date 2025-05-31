import os
import sys
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QFileDialog, QMessageBox, QRadioButton, QGroupBox
)
# tools/batch_rename.py
from PyQt6.QtGui import QIcon

TOOL_NAME = "批量重命名工具"
DESCRIPTION = "批量重命名文件夹中的文件"

class BatchRenameTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量重命名工具")
        self.setMinimumSize(800, 600)
        self.folder_path = None  # 当前选择的文件夹路径
        self.file_list = []  # 文件夹中的文件列表
        self.rename_mapping = {}  # 文件名映射关系（原文件名 -> 新文件名）
        self._setup_ui()

    def _setup_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()

        # 选择文件夹按钮
        self.folder_label = QLabel("未选择文件夹")
        self.folder_label.setStyleSheet("font-size: 14px; color: #333;")
        select_folder_button = QPushButton("选择文件夹")
        select_folder_button.setStyleSheet("padding: 8px 16px; background: #007bff; color: white; border-radius: 4px;")
        select_folder_button.clicked.connect(self._select_folder)

        # 命名模式选择
        self.mode_group = QGroupBox("命名模式")
        mode_layout = QVBoxLayout()

        self.table_mode = QRadioButton("使用表格命名")
        self.table_mode.setChecked(True)  # 默认选中表格命名
        self.table_mode.toggled.connect(self._toggle_mode)

        self.suffix_mode = QRadioButton("使用后缀命名")
        self.suffix_mode.toggled.connect(self._toggle_mode)

        mode_layout.addWidget(self.table_mode)
        mode_layout.addWidget(self.suffix_mode)
        self.mode_group.setLayout(mode_layout)

        # 表格命名模式控件
        self.table_label = QLabel("未选择表格文件")
        self.table_label.setStyleSheet("font-size: 14px; color: #333;")
        self.select_table_button = QPushButton("选择表格文件 (CSV/Excel)")
        self.select_table_button.setStyleSheet("padding: 8px 16px; background: #28a745; color: white; border-radius: 4px;")
        self.select_table_button.clicked.connect(self._select_table_file)

        # 后缀命名模式控件
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("前缀（可选）")
        self.prefix_input.setStyleSheet("padding: 8px; border-radius: 4px; border: 1px solid #ccc;")
        self.prefix_input.textChanged.connect(self._update_preview)

        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("后缀（可选）")
        self.suffix_input.setStyleSheet("padding: 8px; border-radius: 4px; border: 1px solid #ccc;")
        self.suffix_input.textChanged.connect(self._update_preview)

        # 文件列表
        self.file_list_widget = QListWidget()
        self.file_list_widget.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; padding: 8px;")

        # 导出文件名按钮
        export_button = QPushButton("导出文件名列表")
        export_button.setStyleSheet("padding: 8px 16px; background: #ffc107; color: black; border-radius: 4px;")
        export_button.clicked.connect(self._export_file_list)

        # 执行重命名按钮
        rename_button = QPushButton("执行重命名")
        rename_button.setStyleSheet("padding: 8px 16px; background: #dc3545; color: white; border-radius: 4px;")
        rename_button.clicked.connect(self._rename_files)
        # 返回按钮
        return_button = QPushButton("返回工具箱")
        return_button.setStyleSheet("padding: 8px 16px; border-radius: 4px; background: #6c757d; color: white;")
        return_button.clicked.connect(self._return_to_toolbox)

        # 布局
        layout.addWidget(self.folder_label)
        layout.addWidget(select_folder_button)
        layout.addWidget(self.mode_group)
        layout.addWidget(self.table_label)
        layout.addWidget(self.select_table_button)
        layout.addWidget(self.prefix_input)
        layout.addWidget(self.suffix_input)
        layout.addWidget(QLabel("文件列表:"))
        layout.addWidget(self.file_list_widget)
        layout.addWidget(export_button)
        layout.addWidget(rename_button)
        layout.addWidget(return_button)
        self.setLayout(layout)

        # 初始化界面状态
        self._toggle_mode()

    def _select_folder(self):
        """选择文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            self.folder_path = folder_path
            self.folder_label.setText(f"已选择文件夹: {folder_path}")
            self._load_files()

    def _select_table_file(self):
        """选择表格文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择表格文件", "", "CSV 文件 (*.csv);;Excel 文件 (*.xlsx)"
        )
        if file_path:
            self.table_label.setText(f"已选择表格文件: {file_path}")
            self._load_rename_mapping(file_path)

    def _load_files(self):
        """加载文件夹中的文件"""
        if not self.folder_path:
            return

        self.file_list_widget.clear()
        self.file_list = []
        for file_name in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, file_name)
            if os.path.isfile(file_path):  # 只处理文件，忽略文件夹
                self.file_list.append(file_name)
                self.file_list_widget.addItem(file_name)

    def _load_rename_mapping(self, file_path):
        """从表格文件中加载文件名映射关系"""
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            elif file_path.endswith(".xlsx"):
                df = pd.read_excel(file_path)
            else:
                QMessageBox.warning(self, "提示", "不支持的文件格式！")
                return

            # 检查表格是否包含必要的列
            if "原文件名" not in df.columns or "新文件名" not in df.columns:
                QMessageBox.warning(self, "提示", "表格文件必须包含 '原文件名' 和 '新文件名' 两列！")
                return

            # 构建文件名映射关系
            self.rename_mapping = dict(zip(df["原文件名"], df["新文件名"]))
            self._update_file_list()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载表格文件失败: {str(e)}")

    def _update_file_list(self):
        """更新文件列表，显示新文件名"""
        self.file_list_widget.clear()
        for file_name in self.file_list:
            new_name = self.rename_mapping.get(file_name, file_name)  # 如果没有映射关系，显示原文件名
            self.file_list_widget.addItem(f"{file_name} -> {new_name}")

    def _update_preview(self):
        """更新后缀命名模式的预览"""
        if not self.suffix_mode.isChecked():
            return

        prefix = self.prefix_input.text()
        suffix = self.suffix_input.text()

        self.file_list_widget.clear()
        for index, file_name in enumerate(self.file_list):
            name, ext = os.path.splitext(file_name)
            new_name = f"{prefix}{name}{suffix}{ext}"
            self.file_list_widget.addItem(f"{file_name} -> {new_name}")

    def _rename_files(self):
        """执行重命名"""
        if not self.folder_path:
            QMessageBox.warning(self, "提示", "请先选择文件夹！")
            return

        if self.table_mode.isChecked():
            if not self.rename_mapping:
                QMessageBox.warning(self, "提示", "请先选择表格文件！")
                return
            self._rename_with_table()
        else:
            self._rename_with_suffix()

    def _rename_with_table(self):
        """使用表格命名模式重命名文件"""
        for old_name, new_name in self.rename_mapping.items():
            old_path = os.path.join(self.folder_path, old_name)
            old_name = str(old_name)
            new_name = str(new_name)
            new_path = os.path.join(self.folder_path, new_name)

            if not os.path.exists(old_path):
                QMessageBox.warning(self, "提示", f"文件 '{old_name}' 不存在！")
                continue

            try:
                os.rename(old_path, new_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名失败: {str(e)}")
                return

        QMessageBox.information(self, "成功", "文件重命名完成！")
        self._load_files()  # 刷新文件列表

    def _rename_with_suffix(self):
        """使用后缀命名模式重命名文件"""
        prefix = self.prefix_input.text()
        suffix = self.suffix_input.text()

        for file_name in self.file_list:
            old_path = os.path.join(self.folder_path, file_name)
            name, ext = os.path.splitext(file_name)
            new_name = f"{prefix}{name}{suffix}{ext}"
            new_path = os.path.join(self.folder_path, new_name)

            try:
                os.rename(old_path, new_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名失败: {str(e)}")
                return

        QMessageBox.information(self, "成功", "文件重命名完成！")
        self._load_files()  # 刷新文件列表

    def _export_file_list(self):
        """导出文件名列表为 Excel 文件"""
        if not self.folder_path:
            QMessageBox.warning(self, "提示", "请先选择文件夹！")
            return

        # 获取保存路径
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件名列表", "", "Excel 文件 (*.xlsx)"
        )
        if not save_path:
            return

        # 构建 DataFrame
        df = pd.DataFrame({"文件名": self.file_list})

        try:
            df.to_excel(save_path, index=False)
            QMessageBox.information(self, "成功", f"文件名列表已导出到: {save_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def _toggle_mode(self):
        """切换命名模式"""
        if self.table_mode.isChecked():
            self.table_label.setVisible(True)
            self.select_table_button.setVisible(True)
            self.prefix_input.setVisible(False)
            self.suffix_input.setVisible(False)
        else:
            self.table_label.setVisible(False)
            self.select_table_button.setVisible(False)
            self.prefix_input.setVisible(True)
            self.suffix_input.setVisible(True)
        self._update_preview()
    def _return_to_toolbox(self):
        """返回工具箱"""
        if self.return_to_toolbox:
            self.return_to_toolbox()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BatchRenameTool()
    window.show()
    sys.exit(app.exec())
class ToolWindow(BatchRenameTool):
    def __init__(self, parent=None):
        super().__init__()
        self.return_to_toolbox = None  # 返回工具箱的函数

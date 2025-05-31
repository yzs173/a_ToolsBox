import sys
import importlib
from pathlib import Path
from PyQt6.QtCore import (QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
                         Qt, QSize, QPoint)
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout,
                            QPushButton, QLabel, QScrollArea, QGraphicsDropShadowEffect,
                            QStackedWidget)

# 配置项
TOOLS_DIR = Path(__file__).parent / "tools"
TOOL_ICON_SIZE = QSize(72, 72)
CARD_STYLE = """
QWidget#ToolCard {
    background: white;
    border-radius: 12px;
    padding: 16px;
}
QWidget#ToolCard:hover {
    background: #f8f9fa;
}
QLabel#ToolTitle {
    color: #212529;
    font-size: 14px;
    font-weight: 500;
    margin-top: 8px;
}
QLabel#ToolDesc {
    color: #6c757d;
    font-size: 12px;
}
"""

class ToolCard(QWidget):
    def __init__(self, tool_info, parent=None):
        super().__init__(parent)
        self.tool_info = tool_info
        self.setObjectName("ToolCard")
        self.setFixedSize(160, 160)
        self._setup_ui()
        self._add_effects()

    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题和描述
        self.title = QLabel(self.tool_info["name"])
        self.title.setObjectName("ToolTitle")
        self.desc = QLabel(self.tool_info["description"])
        self.desc.setObjectName("ToolDesc")
        self.desc.setWordWrap(True)

        layout.addWidget(self.title, 0, 0, 1, 1)
        layout.addWidget(self.desc, 1, 0, 1, 1)

    def _add_effects(self):
        # 悬停阴影动画
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)

        self.anim_group = QParallelAnimationGroup()
        
        # 悬停放大动画
        self.scale_anim = QPropertyAnimation(self, b"geometry")
        self.scale_anim.setDuration(200)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # 阴影强度动画
        self.shadow_anim = QPropertyAnimation(self.shadow, b"color")
        self.shadow_anim.setDuration(200)

        self.anim_group.addAnimation(self.scale_anim)
        self.anim_group.addAnimation(self.shadow_anim)

    def enterEvent(self, event):
        start = self.geometry()
        end = start.adjusted(-4, -4, 4, 4)
        self.scale_anim.setStartValue(start)
        self.scale_anim.setEndValue(end)
        
        self.shadow_anim.setStartValue(QColor(0, 0, 0, 30))
        self.shadow_anim.setEndValue(QColor(0, 0, 0, 50))
        
        self.anim_group.start()

    def leaveEvent(self, event):
        self.anim_group.setDirection(QPropertyAnimation.Direction.Backward)
        self.anim_group.start()

class ToolboxWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tools = self._load_tools()
        self._setup_window()
        self._setup_ui()
        self.setStyleSheet(CARD_STYLE)

    def _setup_window(self):
        self.setWindowTitle("高级工具箱")
        self.setMinimumSize(800, 600)
        self.setWindowIcon(QIcon("icon.png"))
        
        # 主容器
        self.stack = QStackedWidget()  # 使用堆栈布局
        self.setCentralWidget(self.stack)

        # 工具盒页面
        self.toolbox_page = QWidget()
        self.toolbox_layout = QGridLayout(self.toolbox_page)
        self.stack.addWidget(self.toolbox_page)

    def _load_tools(self):
        tools = []
        for f in TOOLS_DIR.glob("*.py"):
            if f.stem.startswith("_"): continue
            try:
                module = importlib.import_module(f"tools.{f.stem}")
                tools.append({
                    "name": module.TOOL_NAME,
                    "description": module.DESCRIPTION,
                    "module": module
                })
            except Exception as e:
                print(f"加载工具失败: {f.stem} - {str(e)}")
        return tools

    def _setup_ui(self):
        row, col = 0, 0
        max_cols = 4
        
        for tool in self.tools:
            card = ToolCard(tool)
            card.mousePressEvent = lambda e, m=tool["module"]: self._open_tool(m)
            self.toolbox_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _open_tool(self, module):
        """打开子工具"""
        tool_window = module.ToolWindow(self)
        tool_window.return_to_toolbox = self._return_to_toolbox  # 传递返回函数
        self.stack.addWidget(tool_window)
        self.stack.setCurrentWidget(tool_window)

    def _return_to_toolbox(self):
        """返回工具箱"""
        current_tool = self.stack.currentWidget()
        if current_tool != self.toolbox_page:
            self.stack.removeWidget(current_tool)  # 移除子工具窗口
            self.stack.setCurrentWidget(self.toolbox_page)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ToolboxWindow()
    window.show()
    sys.exit(app.exec())

import sys

from loguru import logger as log
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from time import sleep
from wuthering import POOLTYPE, TITLE, PoolData, WutheringData, STANDARD_POOL, VERSION, AUTHOR

def spin(index):
    return "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[index]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        self.setFixedSize(QSize(300, 100))

        self.backend = WutheringData()
        self.tick_count = 0

        layout = QVBoxLayout()
        widget = QWidget()

        self.context = QLabel("你好，鳴神")
        layout.addWidget(self.context, alignment=Qt.AlignmentFlag.AlignCenter)

        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.statusBar().showMessage(f"{TITLE} v.{VERSION} | 這我: {AUTHOR}")
        self.show()

        self.tick = QTimer()
        self.tick.setInterval(42)
        self.tick.timeout.connect(self.detect_game)
        self.tick.start()

    def detect_game(self):
        if self.tick_count%29 == 0 and self.backend.locate_executable():
            self.context.setText(f"鳴神，啟動！")
            sleep(2) # for memes 
            self.tick.timeout.disconnect(self.detect_game)
            self.tick.timeout.connect(self.fetch_payload)
        else:
            self.context.setText(
                f"{spin(self.tick_count%10)} 正在等待鳴神啟動"
            )
        self.tick_count += 1

    def fetch_payload(self):
        if self.tick_count%30 == 0 and self.backend.fetch_payload():
            self.context.setText("正在取得管道")
            self.tick.timeout.disconnect(self.fetch_payload)
            self.context.setText("正在整理數據")
            self.backend.populate_data()
            self.context.setText("完成")
            self.dropdown_update()
        else:
            self.context.setText(
                f"{spin(self.tick_count%10)} 缺少資料，請開啟遊戲內抽卡紀錄"
            )
        self.tick_count += 1

    def dropdown_update(self, selection: str = POOLTYPE[1]):
        self.setFixedSize(QSize(300, 180))

        widget = QWidget()
        layout = QVBoxLayout()
        dropdown = QComboBox()
        
        dropdown.addItems([k for k, v in self.backend.data.items() if v.attempt])
        dropdown.setCurrentText(selection)
        dropdown.currentTextChanged.connect(self.dropdown_update)

        layout.addWidget(dropdown)
        content_layout = self.result_content(selection)
        layout.addLayout(content_layout)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def result_content(self, pool: str) -> None:
        data: PoolData = self.backend.data[pool]
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        five_ratio = f"{data.get_ratio(5)*100:.2f}%"
        five_avg = f"{data.get_average(5)}抽"
        four_ratio = f"{data.get_ratio(4)*100:.2f}%"
        four_avg = f"{data.get_average(4)}抽"
        layout.addWidget(QLabel(
            (
                f"抽取次數:  　{data.attempt  }\n"
                f"目前保底:  　{data.get_pity }\n"
                f"5星概率: 　　{five_ratio    }\n"
                f"5星平均: 　　{five_avg      }\n"
                f"4星概率: 　　{four_ratio    }\n"
                f"4星平均: 　　{four_avg      }\n"
            )
        ))
        right_col = QVBoxLayout()
        _history = [
            f"{prefix}{_.name}[{_.pity}]"
            for _ in data.get_history(5)
            if (prefix := "_"
            if pool == "角色活動" and _.name in STANDARD_POOL
            else " ")
        ]
        history = "\n".join(_history[:5])
        right_col.addWidget(QLabel(f"最近紀錄: \n{history}"))
        right_col.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addLayout(right_col)
        return layout
        

if __name__ == "__main__":
    log.remove()
    # log.add(sys.stdout, level="DEBUG")
    app = QApplication()
    window = MainWindow()

    app.exec()

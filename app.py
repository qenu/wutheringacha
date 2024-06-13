from time import sleep

from loguru import logger as log
from PySide6.QtCore import QSize, QTimer
from PySide6.QtGui import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QFrame,
)
from wuthering import (
    AUTHOR,
    POOLTYPE,
    STANDARD_POOL,
    TITLE,
    VERSION,
    PoolData,
    WutheringData,
)


def spin(index):
    return "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[index]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        log.debug("Created QMainWindow")
        self.setWindowTitle("鳴潮卡池紀錄")
        self.setFixedSize(QSize(300, 100))

        self.backend = WutheringData()
        self.tick_count = 0

        layout = QVBoxLayout()
        widget = QWidget()

        self.center_text = QLabel("你好，鳴潮")
        layout.addWidget(
            self.center_text, alignment=Qt.AlignmentFlag.AlignCenter
        )

        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.statusBar().showMessage(
            f"{TITLE} v{VERSION} | 這我: {AUTHOR}"
        )
        self.show()

        log.debug("Starting QTimer")
        self.tick = QTimer()
        self.tick.setInterval(42)
        self.tick.timeout.connect(self.detect_game)
        self.tick.start()

    def detect_game(self):
        if self.tick_count % 29 == 0 and self.backend.locate_executable():
            log.debug("Game detected")
            self.center_text.setText(f"鳴潮，啟動！")
            sleep(1)  # for memes
            self.tick.timeout.disconnect(self.detect_game)
            self.tick.timeout.connect(self.fetch_payload)
        else:
            self.center_text.setText(
                f"{spin(self.tick_count%10)} 正在等待鳴潮啟動"
            )
        self.tick_count += 1

    def fetch_payload(self):
        if self.tick_count % 29 == 0 and self.backend.fetch_payload():
            log.debug("Created Payload for API request")
            self.tick.timeout.disconnect(self.fetch_payload)
            self.tick.timeout.connect(self.populate_data)
        else:
            self.center_text.setText(
                f"{spin(self.tick_count%10)} 缺少資料，請開啟遊戲內抽卡紀錄"
            )
        self.tick_count += 1

    def populate_data(self):
        log.debug("Populating data from pool")
        if self.tick_count % 18 == 0:
            self.center_text.setText("完成")
            self.repaint()
            self.backend.populate_data()
            self.tick.timeout.disconnect(self.populate_data)
            self.tick.stop()
            self.dropdown_update()
        else:
            self.center_text.setText(
                f"{spin(self.tick_count%10)} 正在整理數據"
            )
        self.tick_count += 1

    def dropdown_update(self, selection: str = POOLTYPE[1]):
        log.debug("Refreshed center Dropdown Widget")
        self.setFixedSize(QSize(300, 420))

        widget = QWidget()
        layout = QVBoxLayout()
        dropdown = QComboBox()

        dropdown.addItems(
            [k for k, v in self.backend.data.items() if v and v.attempt]
        )
        dropdown.setCurrentText(selection)
        dropdown.currentTextChanged.connect(self.dropdown_update)

        layout.addWidget(dropdown)
        content_layout = self.result_content(selection)
        layout.addLayout(content_layout)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def result_content(self, pool: str) -> None:
        log.debug("Content created")
        data: PoolData = self.backend.data[pool]
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        five_ratio = f"{data.get_ratio(5)*100:.2f}%"
        five_avg = f"{data.get_average(5)}抽"
        five_pool = data.entry.get(5, [])
        four_ratio = f"{data.get_ratio(4)*100:.2f}%"
        four_avg = f"{data.get_average(4)}抽"
        four_pool = data.entry.get(4, [])
        four_char = [
            _ for _ in data.entry.get(4, []) if _.resourcetype == "角色"
        ]
        four_weap = [
            _ for _ in data.entry.get(4, []) if _.resourcetype == "武器"
        ]
        optional = ""
        cum = data.get_history(5)
        if cum and pool == "角色活動":
            hit_miss = (
                len([_ for _ in cum if _.name not in STANDARD_POOL])
                / len(cum)
                * 100
            )
            optional = f"保底命中:  　{hit_miss:.2f}%"

        desc = QLabel(
            (
                f"抽取次數:  　{data.attempt  }\n"
                f"目前保底:  　{data.get_pity }\n"
                f"{optional}\n"
                "\n5星\n"
                f"　概率: 　　{five_ratio    }\n"
                f"　平均: 　　{five_avg      }\n"
                f"　總計: 　　{len(five_pool)}\n"
                "\n4星\n"
                f"　概率: 　　{four_ratio    }\n"
                f"　平均: 　　{four_avg      }\n"
                f"　總計: 　　{len(four_pool)}\n"
                "\n4星角色\n"
                f"　概率: 　　{len(four_char)}\n"
                f"　總計: 　　{len(four_char)/len(four_pool):.2f}%\n"
                "\n4星武器\n"
                f"　概率: 　　{len(four_weap)}\n"
                f"　總計: 　　{len(four_weap)/len(four_pool):.2f}%\n"
            )
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        desc.setFixedWidth(140)
        layout.addWidget(desc)

        right_col = QVBoxLayout()
        right_col.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        right_col.addWidget(QLabel("最近紀錄"))

        log.debug("Pool cum data: {}", cum)
        scroll = QScrollArea()
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setWidgetResizable(True)
        inner = QFrame(scroll)
        inner.setLayout(QVBoxLayout())
        inner.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(inner)
        for item in cum:
            label = QLabel(f"{item.name:　<5}{item.pity:>2}抽")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            label.setStyleSheet("color: cornflowerblue")
            if pool == "角色活動" and item.name in STANDARD_POOL:
                label.setStyleSheet("color: orangered")
            inner.layout().addWidget(label)

        right_col.addWidget(scroll)
        layout.addLayout(right_col)
        return layout


if __name__ == "__main__":
    log.remove()
    import sys

    log.add(sys.stdout, level="DEBUG")
    app = QApplication()
    window = MainWindow()
    log.debug("App Start")
    app.exec()

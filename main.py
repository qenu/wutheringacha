import os
import re
import sys
from datetime import datetime
from time import sleep

import requests
from loguru import logger as log
from psutil import Process, pids, NoSuchProcess
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel

from const import (
    API_URL,
    EXE_NAME,
    FETCH_URL,
    LOG_PATH_EXTEND,
    POOLTYPE,
    STANDARD_POOL,
    TEMP_PAYLOAD,
    VERSION,
)


class PoolNode:
    def __init__(
        self,
        name: str,
        resourcetype: str,
        pooltype: int,
        qualityLevel: int,
        time: int,
        attempt: int,
        pity: int,
    ):
        self.name = name
        self.resourcetype = resourcetype
        self.pooltype = pooltype
        self.qualityLevel = qualityLevel
        self.time = time
        self.attempt = attempt
        self.pity = pity

    def __repr__(self) -> str:
        return f"[{self.resourcetype}]{self.name}: {self.pity}@{self.time}"

    @property
    def _rich_repr_(self) -> str:
        color = "yellow" if self.qualityLevel == 5 else "purple"
        return f"[{color}]{self.name}[{self.pity}][/{color}]"


class PoolData:
    def __init__(self):
        self.entry: dict[int, list[PoolNode]] = {}
        self.attempt = 0

    def load(self, data: list) -> None:
        log.info("Loading PoolData...")
        self.attempt = 0
        self.entry[4] = []
        self.entry[5] = []

        for item in data[::-1]:
            self.attempt += 1
            log.debug(
                "{attempt} Item: {item}, Quality: {qualityLevel}",
                attempt=self.attempt,
                item=item["name"],
                qualityLevel=item["qualityLevel"],
            )
            if item["qualityLevel"] < 4:
                continue
            _entry = self.entry.get(item["qualityLevel"], []).copy()
            if item["qualityLevel"] == 4:
                _entry.extend(self.entry.get(5, []))
                _entry = sorted(_entry, key=lambda x: x.attempt)

            node = PoolNode(
                name=item["name"],
                resourcetype=item["resourceType"],
                pooltype=item["cardPoolType"],
                qualityLevel=item["qualityLevel"],
                time=int(
                    datetime.strptime(item["time"], "%Y-%m-%d %H:%M:%S").timestamp()
                ),
                attempt=self.attempt,
                pity=self.attempt - (0 if not _entry else _entry[-1].attempt),
            )
            log.debug("Found {name} {qualityLevel} {resourceType}", **item)
            log.debug("Node: {node}", node=node)
            self.entry[item["qualityLevel"]].append(node)
        log.info("Loaded {attempt} entries", attempt=self.attempt)
        log.info("4 Star: {count}", count=len(self.entry.get(4, [])))
        log.info("5 Star: {count}", count=len(self.entry.get(5, [])))
        log.debug("Entry: {entry}", entry=self.entry)

        return self  # for chaining

    def get_ratio(self, quality: int) -> float:
        if not self.entry.get(quality):
            return 0.0
        return round(len(self.entry[quality]) / self.attempt, 6)

    def get_average(self, quality: int) -> float:
        if not self.entry.get(quality):
            return 0.0
        return round(
            sum([_.pity for _ in self.entry[quality]]) / len(self.entry[quality]),
            2,
        )

    def get_latest(self, quality: int, miss: bool = False) -> str:
        if not self.entry.get(quality):
            return "無"
        result = []
        for it, item in enumerate(
            self.entry[quality][: min(20, len(self.entry[quality]))][::-1]
        ):
            if miss and item.name in STANDARD_POOL:
                result.append(f"[red]{item.name}[{item.pity}][/red]")
            else:
                result.append(f"{item._rich_repr_}")
        return ", ".join(result)

    def output(self, title: str) -> Panel:
        current_pity = (
            self.attempt - _[-1].attempt if (_ := self.entry.get(5, None)) else 0
        )
        return Panel(
            (
                f"[b]{title}[/b]\n"
                "-------------------\n"
                f"抽取次数: {self.attempt}\n"
                f"目前保底數量: {current_pity}\n"
                "[yellow]"
                f"5星概率: {self.get_ratio(5)*100:.2f}%\n"
                f"5星平均: {self.get_average(5)}抽\n"
                "[/yellow][purple]"
                f"4星概率: {self.get_ratio(4)*100:.2f}%\n"
                f"4星平均: {self.get_average(4)}抽\n"
                "[/purple]"
                "-------------------\n"
                f"最近紀錄: \n{self.get_latest(5, (title == '角色活動卡池紀錄'))}\n"
            ),
            width=26,
        )


class WutheringData:
    def __init__(self):
        log.info("Initialize WutheringData...")
        self.payload: dict[str, str] = {}
        self.data: dict[str, PoolData | None] = {}
        self._logfile = ""

    def locate_executable(self, timeout: int = 30) -> bool:
        t = 0
        while True:
            for id in pids():
                try:
                    if Process(id).name() == EXE_NAME:
                        executable = Process(id).exe()
                        log.debug("Caught executable {exe}", exe=executable)
                        paths = os.path.normpath(executable).split(os.path.sep)
                        paths.insert(1, os.path.sep)
                        log.debug("Executable path: {path}", path=paths)
                        self._logfile = os.path.join(
                            *paths[: paths.index("Client") + 1], *LOG_PATH_EXTEND
                        )
                        log.debug("Log file path: {path}", path=self._logfile)
                        return True
                except NoSuchProcess:
                    pass
            t += 1
            if t >= timeout:
                return False
            sleep(1)

    def fetch_payload(self, timeout: int = 30) -> bool:
        t = 0
        url = ""
        while url == "":
            with open(self._logfile, "r", encoding="utf-8") as file:
                for line in file:
                    if FETCH_URL in line:
                        url = line
                        break
            t += 1
            if t >= timeout:
                return False
            sleep(1)

        regex = re.search(f'{FETCH_URL[-9:]}[^"]*', line)
        partial = {
            foo[0]: foo[1] for _ in regex[0][9:].split("&") if (foo := _.split("="))
        }
        log.debug("^ {partial}", partial=partial)
        log.info("Creating Payload")
        payload = TEMP_PAYLOAD.copy()
        for k, v in payload.items():
            payload[k] = partial.get(v, None)
        log.debug("^ {payload}", payload=payload)
        self.payload = payload
        return True

    def fetch_data(self, pool: int = 1) -> PoolData | None:
        payload = self.payload.copy()
        payload["cardPoolType"] = pool
        resp = requests.post(API_URL, json=payload)
        if resp.status_code != 200:
            log.warning("Request Failed, Please refresh game log.")
            raise KeyError("Server not responding to info.")
        data = resp.json()["data"]
        if not data:
            log.warning("No data found for {pool}.", pool=POOLTYPE[pool])
            return None
        return PoolData().load(data)

    def populate_data(self) -> None:
        for key, name in POOLTYPE.items():
            log.info("Fetching {name} PoolData", name=name)
            self.data[name] = self.fetch_data(key)

    def output(self) -> list:
        return [
            self.data[name].output(name + "卡池紀錄")
            for name in POOLTYPE.values()
            if self.data.get(name)
        ]


if __name__ == "__main__":
    log.remove()
    log.add(sys.stdout, level="WARNING")
    # log.add(sys.stdout, level="INFO")
    # log.add(sys.stdout, level="DEBUG")
    log.add("wuthering.log", level="DEBUG")

    console = Console()
    with console.status("[bold cyan]請保持遊戲開啟，確認遊戲執行中...") as status:
        wd = WutheringData()
        if not wd.locate_executable():
            status.update("[bold red]讀取遊戲失敗或者超時，使用輸入鍵結束...")
            console.input("")
            sys.exit()
        else:
            status.update("[bold green]遊戲執行確認完成")

    with console.status(
        "[bold cyan]嘗試讀取玩家資料，請開啟抽卡記錄頁面繼續..."
    ) as status:
        if not wd.fetch_payload():
            status.update("[bold red]API讀取超時，使用輸入鍵結束...")
            console.input("")
            sys.exit()
        else:
            status.update("[bold green]資料讀取確認")

    with console.status("[bold cyan]開始請求玩家抽卡紀錄整理...") as status:
        wd.populate_data()

    console.print(Columns(wd.output()))
    console.print(f"[bold blue]Wuthering Gacha")
    console.print(f"[grey]Version: {VERSION}")
    console.print("[grey]Author: attn_deficit")
    console.input("使用輸入鍵結束...")
    sys.exit()

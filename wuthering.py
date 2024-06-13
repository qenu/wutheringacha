TITLE = "Wuthering Gacha"
VERSION = "3.1.0"
AUTHOR = "attn_deficit"

PATH = [
    "Wuthering Waves",
    "Wuthering Waves Game",
    "Client",
    "Saved",
    "Logs",
]
FETCH_URL = "https://aki-gm-resources-oversea.aki-game.net/aki/gacha/index.html#/record?"
API_URL = "https://gmserver-api.aki-game2.net/gacha/record/query"

EXE_NAME = "Client-Win64-Shipping.exe"
LOG_PATH_EXTEND = ["Saved", "Logs", "Client.log"]

TEMP_PAYLOAD = {
    "serverId": "svr_id",
    "playerId": "player_id",
    "languageCode": "lang",
    "recordId": "record_id",
    "cardPoolId": "resources_id",
}

POOLTYPE = {
    1: "角色活動",
    2: "武器活動",
    3: "角色常駐",
    4: "武器常駐",
    # 5: "新手池",
    # 6: "新手定向"
}

STANDARD_POOL = ["安可", "鑒心", "維里奈", "卡卡羅", "凌陽"]


import os
import re
from datetime import datetime
from subprocess import CalledProcessError, check_output

import requests
from loguru import logger as log
from psutil import NoSuchProcess, Process


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
        return (
            f"[{self.resourcetype}]{self.name}: {self.pity}@{self.time}"
        )

    @property
    def _color(self) -> str:
        return "yellow" if self.qualityLevel == 5 else "purple"


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
                    datetime.strptime(
                        item["time"], "%Y-%m-%d %H:%M:%S"
                    ).timestamp()
                ),
                attempt=self.attempt,
                pity=self.attempt
                - (0 if not _entry else _entry[-1].attempt),
            )
            log.debug(
                "Found {name} {qualityLevel} {resourceType}", **item
            )
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
            sum([_.pity for _ in self.entry[quality]])
            / len(self.entry[quality]),
            2,
        )

    def get_history(self, quality: int) -> list[PoolNode]:
        if not self.entry.get(quality, False):
            return []
        return [
            _
            for _ in self.entry[quality][
                : min(20, len(self.entry[quality]))
            ][::-1]
        ]

    @property
    def get_pity(self) -> int:
        return (
            self.attempt - _[-1].attempt
            if (_ := self.entry.get(5, None))
            else 0
        )


class WutheringData:
    def __init__(self):
        log.info("Initialize WutheringData...")
        self.payload: dict[str, str] = {}
        self.data: dict[str, PoolData | None] = {}
        self._logfile = ""

    def locate_executable(self) -> bool:
        try:
            id = check_output(f'tasklist | find "{EXE_NAME}"', shell=True)
            log.debug("id found: {}", id)
            if not id:
                return False
            id = int(id.split()[1])
            log.debug("id found: {}", id)
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
        except CalledProcessError as e:
            pass
        return False

    def fetch_payload(self) -> bool:
        url = ""
        with open(self._logfile, "r", encoding="utf-8") as file:
            for line in file:
                if FETCH_URL in line:
                    url = line
                    break

        if url == "":
            return False
        # url = TESTING_ONLY_URL

        log.debug("Found url: {}", url)

        regex = re.search(f'{FETCH_URL[-9:]}[^"]*', url)
        partial = {
            foo[0]: foo[1]
            for _ in regex[0][9:].split("&")
            if (foo := _.split("="))
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
        if self.payload == {}:
            raise ValueError("Payload empty")
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

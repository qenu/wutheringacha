from dynaconf import Dynaconf, loaders
from dynaconf.utils.boxing import DynaBox
from enum import IntEnum
from urllib import parse
from datetime import datetime
import requests
import msgspec

TAGS = "https://raw.githubusercontent.com/qenu/wutheringacha/4.dev.0/resource.json"
LOCALE = "https://raw.githubusercontent.com/qenu/wutheringacha/4.dev.0/locale/{}.json"

SETTINGS_FILE = "settings.toml"

PATH = ""
API = "https://gmserver-api.aki-game2.net/gacha/record/query"

settings = Dynaconf(
    settings_files=[SETTINGS_FILE],
)

def settings_reload():
    data = settings.as_dict()
    loaders.write(SETTINGS_FILE, DynaBox(data).to_dict(), merge=False)

class CONVENE_TYPE(IntEnum):
    character_event:        int = 1
    weapon_event:           int = 2
    character_permanent:    int = 3
    weapon_permanent:       int = 4

class ConveneNode(msgspec.Struct):
    id: int
    time: int

class Convene(msgspec.Struct):
    history: list[ConveneNode] = []

    def load(self, data: dict) -> "Convene":
        self.history = [
                ConveneNode(
                    id=item["id"],
                    time=item["time"]
                ) 
                for item in data
                ]
        return self

class ConveneStat:
    def __init__(self, data: list[ConveneNode], tags: dict):
        self.gold = []
        self.purple = []
        self.gold_rate = 0.0
        self.purple_rate = 0.0
        self.current_pity = 0
        self.total_pulls = 0
        self.load_data(data, tags)

    def load_data(self, data: list[ConveneNode], purple_list):
        for node in data:
            if node.id > 10000:
                pass # 3 star weapon
            elif node.id in purple_list:
                pass # 4 star

class WutherInfo:
    """ WutherInfo Class
    stores payload, nickname and update time
    """
    name: str = ""
    time: int = 0

    server_id: str = ""
    player_id: str = ""
    record_id: str = ""
    pool_id: str = ""
    language_code: str = ""

    def __repr__(self) -> str:
        return (
            f"WutherInfo<{self.name}> "
            f"t={self.time} "
            f"ply={self.player_id} "
            f"svr={self.server_id} "
            f"rec={self.record_id} "
            f"pool={self.pool_id} "
            f"lang={self.language_code}"
        )

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "time": self.time,
            "svr_id": self.server_id,
            "ply_id": self.player_id,
            "rec_id": self.record_id,
            "pool_id": self.pool_id,
            "lang": self.language_code
        }
    
    def loadurl(self, url: str) -> "WutherInfo":
        query = parse.urlsplit(url=url).fragment.split("?")[1]
        parse_dict = dict(parse.parse_qsl(query))
        self.server_id = parse_dict["svr_id"]
        self.player_id = parse_dict["player_id"]
        self.record_id = parse_dict["record_id"]
        self.pool_id = parse_dict["resources_id"]
        self.language_code = parse_dict["lang"]
        return self

    def load(self, data: dict) -> "WutherInfo":
        self.name = data["name"]
        self.time = data["time"]
        self.server_id = data["svr_id"]
        self.player_id = data["ply_id"]
        self.record_id = data["rec_id"]
        self.pool_id = data["pool_id"]
        self.language_code = data["lang"]
        return self

    def payload(self, *,
                server_id: str = "",
                player_id: str = "",
                language_code: str = "",
                record_id: str = "",
                pool_id: str = "",
                ) -> dict:
        return {
            "serverId": server_id or self.server_id,
            "playerId": player_id or self.player_id,
            "languageCode": language_code or self.language_code,
            "recordId": record_id or self.record_id,
            "cardPoolId": pool_id or self.pool_id,
        }

class WutherAccount:
    def __init__(self, info: WutherInfo):
        self.convene: dict[str, Convene] = {}
        self.info: WutherInfo = info

        lang = requests.get(LOCALE.format(self.info.language_code))
        tags = requests.get(TAGS)
        self.locale_name = lang.json()
        self.tags = tags.json()

    def prev_update(self) -> datetime:
        return datetime.fromtimestamp(self.info.time)

    def _get_convene(self, _type: CONVENE_TYPE) -> Convene:
        payload = self.info.payload(pool_id=_type)
        response = requests.post(API, json=payload)
        data = response.json()["data"]
        return Convene(
            history=[
                ConveneNode(
                    id=item["resourceId"],
                    time=int(
                        datetime.strptime(
                            item["time"], "%Y-%m-%d %H:%M:%S"
                        ).timestamp()
                    )
                ) 
                for item in data
                ]
            )

    def get_convene(self):
        for _type in CONVENE_TYPE:
            convene: Convene = self._get_convene(_type)
            self.convene[_type.name] = convene
        self.info.time = int(datetime.timestamp(datetime.now()))

    def save(self) -> None:
        with open(self.info.player_id + ".json", "wb") as f:
            f.write(msgspec.json.Encoder().encode(self.convene))

    def load_convene(self):
        try:
            with open(self.info.player_id + ".json", "rb") as f:
                data = f.read()
        except FileNotFoundError:
            return False
        content = msgspec.json.Decoder().decode(data)
        self.convene = {}
        for k, v in content.items():
            self.convene[k] = Convene().load(v["history"])

    def get_stats(self, convene_key: str):
        if convene_key not in self.convene.keys():
            return 
        stat = ConveneStat(self.convene[convene_key], self.tags)

if __name__ == "__main__":
    foo = "one"
    # info = WutherInfo().loadurl(url=url)
    k = list(settings.accounts.keys())[1]
    d = settings.accounts.get(k)
    info = WutherInfo().load(data=d)
    acc = WutherAccount(info)
    # print(foo)
    # o = acc._get_convene(CONVENE_TYPE.character_permanent)
    # print(len(acc.convene))
    # acc.get_convene()
    # print(acc.convene)
    # acc.save()

    # acc.load_convene()
    # print(len(acc.convene))
    # print(len(acc.convene["character_event"].history))

    # response = requests.post(
    #     API, 
    #     json=acc.info.payload(pool_id=1, language_code="en")
    # )
    # data = response.json()["data"]

    # locale = {}
    # for item in data:
    #     if item["name"] in locale.values():
    #         continue
    #     locale[str(item["resourceId"])] = item["name"]

    # locale = {_: locale[_] for _ in sorted(locale)}
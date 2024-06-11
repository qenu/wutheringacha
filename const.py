VERSION = "2.7"

PATH = ["Wuthering Waves", "Wuthering Waves Game", "Client", "Saved", "Logs"]
FETCH_URL = (
    "https://aki-gm-resources-oversea.aki-game.net/aki/gacha/index.html#/record?"
)
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

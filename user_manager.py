import json
from datetime import datetime
from pathlib import Path


# 這個檔案專門管理 LINE 使用者資料。
# 目前先用 data/users.json 當成簡單資料庫，方便初學階段直接看懂與手動檢查。
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"


def _now_text():
    """回傳目前時間文字，統一存成容易閱讀的格式。"""

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _empty_users_data():
    """建立空的使用者資料結構。"""

    return {"users": []}


def _make_default_user(user_id):
    """建立一筆完整的預設使用者資料。"""

    now = _now_text()
    return {
        "user_id": user_id,
        "display_name": "unknown",
        "favorite_coin": "",
        "onboarded": False,
        "created_at": now,
        "last_seen_at": now,
        "onboarded_at": "",
    }


def _normalize_user(user):
    """把舊格式或不完整的使用者資料補成新版完整格式。"""

    # 舊版如果只有存 user_id 字串，也可以自動轉成完整 dict。
    if isinstance(user, str):
        return _make_default_user(user)

    # 如果資料不是 dict，就代表這筆壞掉了，直接略過。
    if not isinstance(user, dict):
        return None

    user_id = user.get("user_id")
    if not user_id:
        return None

    # 先建立新版預設資料，再用舊資料覆蓋。
    # 這樣舊 users.json 缺少 onboarded / onboarded_at 時，也會自動補上。
    normalized_user = _make_default_user(user_id)
    normalized_user.update(user)

    # 下面幾行是保險處理，避免 None 或空值讓後續顯示出錯。
    normalized_user["display_name"] = normalized_user.get("display_name") or "unknown"
    normalized_user["favorite_coin"] = normalized_user.get("favorite_coin") or ""
    normalized_user["onboarded"] = bool(normalized_user.get("onboarded", False))
    normalized_user["created_at"] = normalized_user.get("created_at") or _now_text()
    normalized_user["last_seen_at"] = normalized_user.get("last_seen_at") or _now_text()
    normalized_user["onboarded_at"] = normalized_user.get("onboarded_at") or ""

    return normalized_user


def _user_to_db_row(user):
    """把 JSON 使用的 user_id 欄位轉成 Supabase users table 的 line_user_id 欄位。"""

    if not isinstance(user, dict):
        return {}

    row = dict(user)
    row["line_user_id"] = row.pop("user_id", row.get("line_user_id", ""))
    return row


def _db_row_to_user(row):
    """把 Supabase users table 的 line_user_id 轉回既有程式使用的 user_id。"""

    if not isinstance(row, dict):
        return None

    user = dict(row)
    user["user_id"] = user.pop("line_user_id", user.get("user_id", ""))
    return _normalize_user(user)


def _sync_user_to_db(user):
    """把單一使用者同步到 Supabase；失敗時保留 JSON，不影響 LINE Bot。"""

    normalized_user = _normalize_user(user)
    if normalized_user is None:
        return False

    try:
        from database_manager import upsert_user
    except Exception as error:
        print(f"[Supabase] 使用者同步模組載入失敗，保留 JSON fallback：{error}")
        return False

    return upsert_user(_user_to_db_row(normalized_user))


def _normalize_data(data):
    """把整份 users.json 整理成固定格式。"""

    # 兼容很早期可能直接存 list 的格式。
    if isinstance(data, list):
        raw_users = data
    elif isinstance(data, dict):
        raw_users = data.get("users", [])
    else:
        raw_users = []

    users = []
    seen_user_ids = set()

    # 用 seen_user_ids 避免同一個 user_id 重複出現在 users.json。
    for raw_user in raw_users:
        user = _normalize_user(raw_user)
        if user is None:
            continue

        user_id = user["user_id"]
        if user_id in seen_user_ids:
            continue

        seen_user_ids.add(user_id)
        users.append(user)

    return {"users": users}


def _save_data(data):
    """把使用者資料寫回 users.json。"""

    normalized_data = _normalize_data(data)

    DATA_DIR.mkdir(exist_ok=True)
    with USERS_FILE.open("w", encoding="utf-8") as file:
        json.dump(normalized_data, file, ensure_ascii=False, indent=4)
        file.write("\n")

    return normalized_data


def _ensure_users_file():
    """確認 data/users.json 存在，而且格式是新版格式。"""

    DATA_DIR.mkdir(exist_ok=True)

    if not USERS_FILE.exists():
        _save_data(_empty_users_data())
        return

    # 每次程式啟動時 normalize 一次，可以自動升級舊資料。
    data = load_users()
    _save_data(data)


def load_users():
    """讀取 users.json，讀不到或 JSON 壞掉時回傳空資料。"""

    DATA_DIR.mkdir(exist_ok=True)

    if not USERS_FILE.exists():
        return _save_data(_empty_users_data())

    try:
        with USERS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        print("users.json 讀取失敗，先使用空的使用者資料，避免程式直接崩潰。")
        data = _empty_users_data()

    return _normalize_data(data)


def save_user(user_id):
    """新增使用者；如果已存在，就只更新 last_seen_at。"""

    data = load_users()
    users = data["users"]

    for user in users:
        if user["user_id"] == user_id:
            user["last_seen_at"] = _now_text()
            saved_data = _save_data(data)
            _sync_user_to_db(user)
            return saved_data

    new_user = _make_default_user(user_id)
    users.append(new_user)
    saved_data = _save_data(data)
    _sync_user_to_db(new_user)
    return saved_data


def get_user(user_id):
    """回傳指定使用者的完整資料；找不到就回傳 None。"""

    try:
        from database_manager import get_user_by_line_id

        db_user = _db_row_to_user(get_user_by_line_id(user_id))
        if db_user is not None:
            return db_user
    except Exception as error:
        print(f"[Supabase] 查詢使用者失敗，改讀 users.json：{error}")

    for user in load_users()["users"]:
        if user["user_id"] == user_id:
            return user

    return None


def mark_user_onboarded(user_id):
    """把使用者標記成已看過新手說明書，並記錄完成時間。"""

    data = save_user(user_id)

    for user in data["users"]:
        if user["user_id"] == user_id:
            user["onboarded"] = True
            user["onboarded_at"] = _now_text()
            user["last_seen_at"] = _now_text()
            saved_data = _save_data(data)
            _sync_user_to_db(user)
            return saved_data

    return _save_data(data)


def update_favorite_coin(user_id, coin):
    """更新使用者最愛幣種。"""

    data = save_user(user_id)
    users = data["users"]

    for user in users:
        if user["user_id"] == user_id:
            # 統一存小寫，顯示給使用者時再轉大寫。
            user["favorite_coin"] = str(coin).strip().lower()
            user["last_seen_at"] = _now_text()
            saved_data = _save_data(data)
            _sync_user_to_db(user)
            return saved_data

    return _save_data(data)


def get_all_users():
    """回傳所有使用者資料，給 scheduler 每日推播使用。"""

    try:
        from database_manager import get_all_users_from_db

        db_users = [_db_row_to_user(row) for row in get_all_users_from_db()]
        db_users = [user for user in db_users if user is not None]
        if db_users:
            return db_users
    except Exception as error:
        print(f"[Supabase] 查詢全部使用者失敗，改讀 users.json：{error}")

    return load_users()["users"]


def show_all_users():
    """在終端機列出所有使用者，方便開發時檢查資料。"""

    users = get_all_users()

    if not users:
        print("目前還沒有任何使用者。")
        return []

    headers = [
        "user_id",
        "favorite_coin",
        "onboarded",
        "created_at",
        "last_seen_at",
        "onboarded_at",
    ]
    rows = [
        [
            user.get("user_id", ""),
            user.get("favorite_coin", ""),
            user.get("onboarded", False),
            user.get("created_at", ""),
            user.get("last_seen_at", ""),
            user.get("onboarded_at", ""),
        ]
        for user in users
    ]

    widths = []
    for index, header in enumerate(headers):
        longest_value = max(len(str(row[index])) for row in rows)
        widths.append(max(len(header), longest_value))

    header_line = " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    separator_line = "-+-".join("-" * width for width in widths)

    print(header_line)
    print(separator_line)

    for row in rows:
        print(" | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))

    return users


# 匯入這個模組時就先確認 users.json 可以使用。
# 這樣 webhook、scheduler、手動測試都不用各自重複處理檔案初始化。
_ensure_users_file()

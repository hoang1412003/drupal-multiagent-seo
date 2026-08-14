"""Log co cau truc va che secret DE QUY truoc khi ghi.

Vi sao phai de quy: secret hiem khi nam o tang mot. No nam trong
`{"request": {"headers": {"Authorization": "Bearer ..."}}}`. Mot ham chi xet
key tang ngoai cung se ghi nguyen token vao log ma khong ai thay - va log thi
duoc gui di, luu tru, va doc boi nhieu nguoi hon database.

Hai duong che, deu can:
1. Theo TEN KHOA: bat ky key nao chua `token`, `password`, ... -> [REDACTED].
2. Theo HINH DANG GIA TRI: chuoi trong mot message tu do van co the la
   `Authorization: Bearer eyJ...`. Che theo mau, khong doi key phai dung ten.

Ham `redact` KHONG sua doi tuong goc: caller thuong con dung tiep chinh dict
do de xu ly nghiep vu.
"""
import json
import re


MAX_DEPTH = 6
MAX_ITEMS = 100
MAX_STRING = 2000
DA_CHE = "[REDACTED]"
CAT_BOT = "...[cat]"

# Khop theo chuoi con SAU KHI bo dau phan cach. Header HTTP that dung gach
# noi (`X-Api-Key`), config dung gach duoi (`api_key`), code dung lien
# (`apikey`) - ca ba phai dinh. Chi liet ke dang lien o day, viec chuan hoa
# do `_khoa_nhay_cam()` lo.
#
# Bo dau phan cach la co y fail-closed: che nham mot khoa vo hai chi mat mot
# it kha nang chan doan, con bo lot mot token la lo bi mat vinh vien.
KHOA_NHAY_CAM = (
    "authorization",
    "cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "apikey",
    "databaseurl",
    "dsn",
)

_MAU_GIA_TRI = (
    # Bearer/Basic trong message tu do.
    re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"),
    # JWT ba doan.
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"),
    # DSN co mat khau: postgresql://user:pass@host/db
    re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s@]+@"),
)


_DAU_PHAN_CACH = re.compile(r"[-_.\s]")


def _khoa_nhay_cam(khoa) -> bool:
    if not isinstance(khoa, str):
        return False
    thap = _DAU_PHAN_CACH.sub("", khoa.casefold())
    return any(phan in thap for phan in KHOA_NHAY_CAM)


def _che_chuoi(gia_tri: str) -> str:
    for mau in _MAU_GIA_TRI:
        gia_tri = mau.sub(DA_CHE, gia_tri)
    if len(gia_tri) > MAX_STRING:
        gia_tri = gia_tri[:MAX_STRING] + CAT_BOT
    return gia_tri


def redact(value, *, max_depth: int = MAX_DEPTH, max_items: int = MAX_ITEMS):
    """Tra ban SAO da che. Khong bao gio sua doi tuong goc."""
    return _redact(value, max_depth, max_items, 0)


def _redact(value, max_depth: int, max_items: int, depth: int):
    if depth > max_depth:
        # Vuot do sau: khong tiep tuc di xuong. Cau truc long nhau qua sau
        # thuong la du lieu ngoai, va di het no la duong de log phinh vo han.
        return "[qua sau]"

    if isinstance(value, str):
        return _che_chuoi(value)
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, dict):
        ket_qua = {}
        for i, (khoa, con) in enumerate(value.items()):
            if i >= max_items:
                ket_qua["[cat]"] = f"con {len(value) - max_items} khoa"
                break
            ket_qua[str(khoa)] = (
                DA_CHE if _khoa_nhay_cam(khoa)
                else _redact(con, max_depth, max_items, depth + 1)
            )
        return ket_qua
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        da_che = [
            _redact(con, max_depth, max_items, depth + 1)
            for con in items[:max_items]
        ]
        if len(items) > max_items:
            da_che.append(f"[cat] con {len(items) - max_items} phan tu")
        return da_che
    # Kieu la: doi sang chuoi roi che theo mau, khong tin __repr__.
    return _che_chuoi(repr(value))


def event(logger, name: str, **safe_fields) -> None:
    """Ghi DUNG MOT dong JSON. Moi field deu di qua redact truoc."""
    ban_ghi = {"event": name}
    ban_ghi.update(redact(safe_fields))
    logger.info(json.dumps(ban_ghi, ensure_ascii=False, sort_keys=True))


class RedactingFilter:
    """Filter cho logging chuan: che ca nhung dong log KHONG qua `event()`.

    Can thiet vi thu vien ben thu ba (requests, psycopg, uvicorn) ghi log theo
    cach cua chung, va chung khong biet gi ve quy uoc cua du an nay.
    """

    def filter(self, record) -> bool:
        try:
            record.msg = _che_chuoi(str(record.msg))
            if record.args:
                record.args = tuple(
                    _che_chuoi(str(arg)) if isinstance(arg, str) else arg
                    for arg in (
                        record.args if isinstance(record.args, tuple)
                        else (record.args,)
                    )
                )
        except Exception:
            # Filter hong TUYET DOI khong duoc lam mat dong log hoac nem loi
            # nguoc vao code nghiep vu.
            pass
        return True

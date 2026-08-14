"""Fingerprint v2: bam DU sau input ma he thong cham diem thuc su doc.

Vi sao khong sua `text_utils.content_hash()` tai cho: ham do nam trong duong
cham diem da khoa cho E1/E5. Sua no lam mat hieu luc phep do. Nen v2 la ham
MOI o lop platform, con v1 giu nguyen cho job legacy trong cua so rollback.

No dong no N2 (`docs/technical-debt.md`): v1 chi bam bon field, trong khi SEO
con doc `url_alias` va `image_alt`. Hau qua cua thieu sot do: editor sua alt
anh xong, bao cao cu KHONG bi danh dau la cu, va cap (node, hash) con bi
dedup - tuc bai da doi nhung khong bao gio duoc cham lai.

Chuoi canonical la `b"v2\\n" + JSON compact`. Prefix version nam TRONG phan
duoc bam de hai phien ban khong bao gio cho cung mot hash tren cung du lieu.
"""
import hashlib
import json


VERSION = 2

# Dung thu tu nay. Doi thu tu la doi hash, ke ca khi noi dung y nguyen.
FIELDS = (
    "title",
    "body",
    "summary",
    "url_alias",
    "meta_description",
    "image_alt",
)


def canonical_bytes(fields) -> bytes:
    """Chuoi byte duoc bam. Tach rieng de test doc duoc chinh xac cai gi vao."""
    ordered = {ten: str(fields.get(ten) or "") for ten in FIELDS}
    payload = json.dumps(ordered, ensure_ascii=False, separators=(",", ":"))
    return f"v{VERSION}\n".encode("utf-8") + payload.encode("utf-8")


def input_fingerprint(fields) -> str:
    return hashlib.sha256(canonical_bytes(fields)).hexdigest()

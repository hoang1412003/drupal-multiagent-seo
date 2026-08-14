"""Cho graph hien hanh dung lai noi dung worker DA fetch, khong fetch lan hai.

Graph goi `drupal_client.fetch_content(node_id)` tu thang 7. Worker moi phai
fetch truoc de kiem fingerprint TRUOC khi goi LLM, nen neu khong co lop nay
thi mot job se doc Drupal hai lan - va te hon, co the doc ra hai revision
khac nhau giua hai lan.

Dung ContextVar chu khong phai bien module: mot tien trinh worker co the
chay nhieu job dong thoi, bien module se lam job nay doc noi dung job kia.
"""
from contextlib import contextmanager
from contextvars import ContextVar


_DANG_HOAT_DONG: ContextVar[tuple | None] = ContextVar(
    "connector_prepared_document", default=None
)


@contextmanager
def activate(connector, external_content_id: str, document):
    """Bat prepared document cho dung mot noi dung, reset chac chan khi ra."""
    token = _DANG_HOAT_DONG.set((connector, external_content_id, document))
    try:
        yield document
    finally:
        _DANG_HOAT_DONG.reset(token)


def active():
    return _DANG_HOAT_DONG.get()


def prepared_for(external_content_id: str):
    """Tra document da fetch neu dung noi dung dang xu ly, con lai la None."""
    hien_tai = _DANG_HOAT_DONG.get()
    if hien_tai is None:
        return None
    _, dang_xu_ly, document = hien_tai
    return document if dang_xu_ly == external_content_id else None

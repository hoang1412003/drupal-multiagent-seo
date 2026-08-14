"""Connector Drupal: doc dung revision, ghi qua result callback compare-and-set.

MOI method goi transport DUNG MOT LAN roi tra ket qua co kieu hoac nem loi co
kieu. Retry/backoff thuoc ve hang doi (`job_queue.fail`), khong thuoc ve day.
Neu ca hai tang cung retry thi mot job loi se goi Drupal 3x3 = 9 lan.

Ghi nguoc KHONG dung JSON:API PATCH. PATCH generic ghi de bat ke ban dang
ghi len revision nao, nen mot job cham cua revision cu se xoa bao cao cua
revision moi. Result callback nhan expected revision + hash va tu choi khi
noi dung da doi - so sanh va ghi nam trong cung mot transaction ben Drupal.
"""
from datetime import datetime, timezone
from urllib.parse import quote

import requests

from drupal_client import _fields_tu_resource
from review_platform.connectors.base import (
    ConnectorAuthError,
    ConnectorHealth,
    ConnectorPayloadError,
    ConnectorRevisionNotFound,
    ConnectorTransientError,
    ContentDocument,
    PendingContent,
    PendingPage,
    WriteBackRequest,
    WriteBackResult,
)


CONTENT_TYPE = "cam_nang"
JSONAPI_HEADERS = {"Accept": "application/vnd.api+json"}
JSON_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
TIMEOUT = (5, 30)
HEALTH_TIMEOUT = (2, 2)
LIMIT_MIN = 1
LIMIT_MAX = 50
RETRY_AFTER_MAX = 600.0
TOAN_VAN_CAM = ("title", "body", "summary")


def _retry_after(headers) -> float | None:
    """Chi hieu delta-seconds. Dang HTTP-date bi bo qua co y - phan tich no
    doi dong ho hai may khop nhau, ma sai lech dong ho se thanh backoff sai."""
    raw = (headers or {}).get("Retry-After")
    if raw is None:
        return None
    try:
        giay = float(str(raw).strip())
    except ValueError:
        return None
    return max(0.0, min(giay, RETRY_AFTER_MAX))


class DrupalConnector:
    def __init__(self, site, credentials, *, request_fn=None):
        self.site = site
        self.credentials = credentials
        # Khong doc env luc import module: connector phai lay credential tu
        # site/secret_ref duoc truyen vao, khong tu bien toan cuc.
        self._request = requests.request if request_fn is None else request_fn

    # ------------------------------------------------------------ transport

    def _goi(self, method, url, *, headers, timeout=TIMEOUT, json=None):
        try:
            response = self._request(
                method,
                url,
                headers=headers,
                auth=(self.credentials.username, self.credentials.password),
                timeout=timeout,
                json=json,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise ConnectorTransientError(f"khong goi duoc Drupal: {exc}") from exc
        return response

    def _phan_loai(self, response, *, la_revision_fetch=False):
        ma = response.status_code
        if ma in (401, 403):
            raise ConnectorAuthError(f"connector_auth: Drupal tra {ma}")
        if ma == 404 and la_revision_fetch:
            raise ConnectorRevisionNotFound("revision khong con ton tai tren Drupal")
        if ma == 429 or ma >= 500:
            raise ConnectorTransientError(
                f"Drupal tra {ma}",
                retry_after_seconds=_retry_after(response.headers),
            )
        if ma >= 400:
            raise ConnectorPayloadError(f"Drupal tu choi request: {ma}")
        return response

    @staticmethod
    def _json(response):
        try:
            payload = response.json()
        except ValueError as exc:
            raise ConnectorPayloadError("response khong phai JSON") from exc
        if not isinstance(payload, dict):
            raise ConnectorPayloadError("response JSON khong phai object")
        return payload

    # ---------------------------------------------------------------- fetch

    def _url_noi_dung(self, external_content_id, external_revision_id, working_copy):
        url = (
            f"{self.site.base_url}/jsonapi/node/article/"
            f"{quote(str(external_content_id), safe='')}"
        )
        if external_revision_id is not None:
            return f"{url}?resourceVersion={quote(f'id:{external_revision_id}', safe='')}"
        if working_copy:
            return f"{url}?resourceVersion={quote('rel:working-copy', safe='')}"
        return url

    def fetch_content(
        self,
        external_content_id: str,
        *,
        external_revision_id: str | None = None,
        working_copy: bool = False,
    ) -> ContentDocument:
        response = self._goi(
            "GET",
            self._url_noi_dung(external_content_id, external_revision_id, working_copy),
            headers=JSONAPI_HEADERS,
        )
        self._phan_loai(response, la_revision_fetch=True)

        resource = self._json(response).get("data")
        if not isinstance(resource, dict) or "attributes" not in resource:
            raise ConnectorPayloadError("response thieu data.attributes")

        attributes = resource["attributes"]
        nid = attributes.get("drupal_internal__nid")
        vid = attributes.get("drupal_internal__vid")
        return ContentDocument(
            fields=_fields_tu_resource(resource),
            raw_content=resource,
            source_url=None if nid is None else f"{self.site.base_url}/node/{nid}",
            # Duong legacy khong biet truoc revision, nen phai lay tu response.
            external_revision_id=(
                external_revision_id if external_revision_id is not None
                else (None if vid is None else str(vid))
            ),
            content_type=CONTENT_TYPE,
            langcode=attributes.get("langcode") or "",
        )

    # -------------------------------------------------------- pending feed

    def list_pending(self, *, after_revision_id: int = 0, limit: int = 50) -> PendingPage:
        gioi_han = max(LIMIT_MIN, min(int(limit), LIMIT_MAX))
        moc = max(0, int(after_revision_id))
        response = self._goi(
            "GET",
            f"{self.site.base_url}/vf-ai/integration/v1/pending"
            f"?after_revision_id={moc}&limit={gioi_han}",
            headers=JSON_HEADERS,
        )
        self._phan_loai(response)

        payload = self._json(response)
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise ConnectorPayloadError("feed thieu mang items")

        items = tuple(self._pending_item(item) for item in raw_items)
        cursor = payload.get("next_after_revision_id")
        if cursor is not None and not isinstance(cursor, int):
            raise ConnectorPayloadError("next_after_revision_id phai la so nguyen")
        return PendingPage(items=items, next_after_revision_id=cursor)

    @staticmethod
    def _pending_item(item) -> PendingContent:
        if not isinstance(item, dict):
            raise ConnectorPayloadError("item cua feed khong phai object")
        for cam in TOAN_VAN_CAM:
            if cam in item:
                raise ConnectorPayloadError(
                    f"feed khong duoc mang toan van: co key '{cam}'"
                )

        revision = item.get("external_revision_id")
        if revision is None and not item.get("legacy_without_revision"):
            raise ConnectorPayloadError(
                "item thieu external_revision_id ma khong danh dau legacy"
            )
        for bat_buoc in ("external_content_id", "content_hash", "content_type", "langcode"):
            if not item.get(bat_buoc):
                raise ConnectorPayloadError(f"item thieu {bat_buoc}")

        return PendingContent(
            external_content_id=item["external_content_id"],
            external_revision_id=None if revision is None else str(revision),
            content_hash=item["content_hash"],
            content_type=item["content_type"],
            langcode=item["langcode"],
            source_url=item.get("source_url"),
            content_hash_version=int(item.get("content_hash_version", 2)),
        )

    # ----------------------------------------------------------- write back

    def write_back(self, request: WriteBackRequest) -> WriteBackResult:
        body = {
            "run_id": str(request.run_id),
            "external_content_id": request.external_content_id,
            "expected_revision_id": request.expected_revision_id,
            "content_hash": request.content_hash,
            "content_hash_version": request.content_hash_version,
            "status": request.status,
            "score": request.score,
            "suggestions": request.suggestions,
            "report_json": request.report_json,
        }
        response = self._goi(
            "POST",
            f"{self.site.base_url}/vf-ai/integration/v1/results",
            headers=JSON_HEADERS,
            json=body,
        )

        # 409 content_superseded KHONG phai loi transport: no la ket qua dung
        # cua compare-and-set khi noi dung da co revision moi hon. Coi no la
        # loi se lam worker retry payload cu len noi dung moi.
        if response.status_code == 409:
            payload = self._json(response)
            if payload.get("code") == "content_superseded":
                return WriteBackResult(outcome="content_superseded")
            raise ConnectorPayloadError(f"409 khong ro ly do: {payload.get('code')}")

        self._phan_loai(response)
        payload = self._json(response)
        outcome = payload.get("outcome")
        if outcome not in ("applied", "already_applied"):
            raise ConnectorPayloadError(f"outcome khong hop le: {outcome}")
        applied = payload.get("applied_revision_id")
        return WriteBackResult(
            outcome=outcome,
            applied_revision_id=None if applied is None else str(applied),
        )

    # --------------------------------------------------------------- health

    def health(self) -> ConnectorHealth:
        """Kiem quyen THAT: capability + feed + doc dung revision neu co item.

        Mot GET collection chung chung tra 200 khong chung minh duoc gi -
        worker van co the that bai vi thieu `view latest version`. Nen o day
        phai cham dung ba nang luc se dung o production.

        Tuyet doi khong goi result callback: health khong duoc tao revision.
        """
        thoi_diem = datetime.now(timezone.utc)
        try:
            response = self._goi(
                "GET",
                f"{self.site.base_url}/vf-ai/integration/v1/capabilities",
                headers=JSON_HEADERS,
                timeout=HEALTH_TIMEOUT,
            )
            self._phan_loai(response)
            capabilities = self._json(response)
            thieu = [
                ten for ten in ("pending_feed", "result_callback", "revision_read")
                if capabilities.get(ten) is not True
            ]
            if thieu:
                return ConnectorHealth(
                    ok=False,
                    status_code=response.status_code,
                    checked_at=thoi_diem,
                    error_code="capability_missing",
                )

            page = self.list_pending(after_revision_id=0, limit=1)
            for item in page.items:
                if item.external_revision_id is not None:
                    self.fetch_content(
                        item.external_content_id,
                        external_revision_id=item.external_revision_id,
                    )
                break

            return ConnectorHealth(
                ok=True,
                status_code=response.status_code,
                checked_at=thoi_diem,
                error_code=None,
            )
        except ConnectorAuthError:
            return self._health_loi(thoi_diem, 403, "auth_failed")
        except ConnectorRevisionNotFound:
            return self._health_loi(thoi_diem, 404, "revision_read_failed")
        except ConnectorPayloadError:
            return self._health_loi(thoi_diem, None, "payload_error")
        except ConnectorTransientError:
            return self._health_loi(thoi_diem, None, "timeout")

    @staticmethod
    def _health_loi(thoi_diem, status_code, ma) -> ConnectorHealth:
        return ConnectorHealth(
            ok=False, status_code=status_code, checked_at=thoi_diem, error_code=ma
        )

"""Test thu cong cho _request_with_retry() trong src/drupal_client.py -
dung ham gia lap (khong goi Drupal that) de kiem tra retry/backoff.

Cach chay:
    .venv\\Scripts\\python.exe scripts\\test_retry.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import requests

from drupal_client import MAX_ATTEMPTS, _request_with_retry


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


def _make_fail_then_succeed(num_failures):
    state = {"count": 0}

    def method(url, **kwargs):
        state["count"] += 1
        if state["count"] <= num_failures:
            raise requests.ConnectionError("gia lap loi ket noi")
        return _FakeResponse(200)

    return method, state


def _make_always_fail(status_code):
    state = {"count": 0}

    def method(url, **kwargs):
        state["count"] += 1
        return _FakeResponse(status_code)

    return method, state


if __name__ == "__main__":
    failed = False

    method, state = _make_fail_then_succeed(2)
    try:
        response = _request_with_retry(method, "http://fake")
        ok = response.status_code == 200 and state["count"] == 3
    except Exception as e:
        ok = False
        print(f"    loi khong mong doi: {e}")
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed = True
    print(f"[{status}] fail 2 lan roi thanh cong -> so lan goi={state['count']} (ky vong 3)")

    method, state = _make_always_fail(500)
    try:
        _request_with_retry(method, "http://fake")
        ok = False
    except requests.HTTPError:
        ok = state["count"] == MAX_ATTEMPTS
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed = True
    print(f"[{status}] luon fail 500 -> so lan goi={state['count']} (ky vong {MAX_ATTEMPTS})")

    method, state = _make_always_fail(404)
    try:
        _request_with_retry(method, "http://fake")
        ok = False
    except requests.HTTPError:
        ok = state["count"] == 1
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed = True
    print(f"[{status}] luon fail 404 -> so lan goi={state['count']} (ky vong 1, khong retry)")

    sys.exit(1 if failed else 0)

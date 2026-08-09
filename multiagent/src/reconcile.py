"""Vong doi soat: bat cac bai lot khi duong event that bai.

Spec: docs/superpowers/specs/2026-08-07-... muc 6.3

Day la LUOI AN TOAN, khong phai duong chinh. No khong can biet VI SAO mot bai
bi lot (service restart, Drupal mat mang, module bi tat, doi state bang drush)
- no chi so trang thai mong muon voi trang thai that roi bu chenh lech. Cung
nguyen ly reconciliation loop ma Kubernetes dung.

Chu ky 5 phut chu khong phai 30 giay: quet thua thi tiet kiem goi API vo ich,
va do tre xau nhat 5 phut chi xay ra trong tinh huong da hong.
"""
import logging

import job_queue as q

logger = logging.getLogger(__name__)


def quet(conn, *, liet_ke=None, enqueue_fn=None, co_that_bai=None) -> int:
    """Quet mot vong, tra so job da xep them.

    Ba phu thuoc tiem duoc de test khong can Drupal lan Postgres.

    Loi tu liet_ke() (Drupal API, mang loi, ...) se VAN VA RA NGOAI. Day la
    loi nguon - neu quet() tu nuot thi tao tang nuot loi them, va khong ai
    biet doi soat da ngung. worker.py co try/except bao quanh quet() de ghi
    log dung chung.

    Loi tu XU LY MOT NODE (KeyError, ValueError, ...) thi LOG VA SKIP NODE DO,
    sao cho nhung node con lai PHAI van duoc xu ly - mot node hong khong giet
    ca luot quyet. Worker se thay log va biet mot node co van de, nhung che
    duoc coi la tinh huong binh thuong cua mot luot (khong phai tat ca, chi
    mot) - dung duoc nhu gap Drupal co node rot.
    """
    if liet_ke is None:
        from drupal_client import liet_ke_can_cham

        liet_ke = liet_ke_can_cham
    if enqueue_fn is None:
        enqueue_fn = q.enqueue
    if co_that_bai is None:
        co_that_bai = q.co_job_that_bai

    da_xep = 0
    for bai in liet_ke():
        try:
            node_id = bai["node_id"]
            chash = bai["content_hash"]
            if bai["hash_da_cham"] == chash:
                continue      # da cham dung noi dung nay roi
            if co_that_bai(conn, node_id, chash):
                # TUYET DOI khong hoi sinh job da dead-letter (spec muc 6.3.1).
                # Bai do chi chay lai duoc qua nut "Cham lai" thu cong, tuc phai
                # co nguoi quyet dinh - dung tinh than "bam cham lai la tieu tien
                # API that".
                continue
            kq = enqueue_fn(conn, node_id, chash, "reconcile")
            if kq and kq.get("status") == q.QUEUED:
                da_xep += 1
        except Exception as e:
            # Mot node trong luot quyet khong xep duoc - KHONG duoc giet ca
            # luot. Log, skip node do, roi tiep tuc phia sau.
            logger.warning("Doi soat loi xu ly node %s: %s", bai, e)
    return da_xep

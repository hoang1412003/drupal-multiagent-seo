"""Dung connector tu cau hinh site. Mot cho duy nhat cho worker va reconcile.

Hai noi tu dung connector rieng se de troi lech - vi du mot ben quen resolve
secret theo `secret_ref` cua site ma dung env mac dinh, va the la vong doi
soat noi vao Drupal cua site khac.
"""
from review_platform import sites
from review_platform.connectors import secrets as connector_secrets
from review_platform.connectors.drupal import DrupalConnector


def connector_cho_site(conn, site_id):
    site = sites.load_site_by_id(conn, site_id)
    return DrupalConnector(site, connector_secrets.resolve(site.secret_ref))

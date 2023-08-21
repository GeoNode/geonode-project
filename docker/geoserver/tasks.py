import os
import logging
import time
import base64
import requests
from pathlib import Path
from invoke import task

logger = logging.getLogger(__name__)


@task
def configure_geoserver(ctx):
    _configure_geoserver_password()
    _initialized(ctx)


def _configure_geoserver_password():
    print(
        "************************configuring Geoserver credentials*****************************"
    )
    GEOSERVER_LB_PORT = os.getenv("GEOSERVER_LB_PORT", 8080)
    GEOSERVER_ADMIN_USER = os.getenv("GEOSERVER_ADMIN_USER", "admin")
    GEOSERVER_ADMIN_PASSWORD = os.getenv("GEOSERVER_ADMIN_PASSWORD", "geoserver")
    GEOSERVER_FACTORY_PASSWORD = os.getenv("GEOSERVER_FACTORY_PASSWORD", "geoserver")
    geoserver_rest_baseurl = f"http://localhost:{GEOSERVER_LB_PORT}/geoserver/rest"
    basic_auth_credentials = base64.b64encode(
        f"{GEOSERVER_ADMIN_USER}:{GEOSERVER_FACTORY_PASSWORD}".encode()
    ).decode()
    headers = {
        "Content-type": "application/xml",
        "Accept": "application/xml",
        "Authorization": f"Basic {basic_auth_credentials}",
    }
    data = f"""<?xml version="1.0" encoding="UTF-8"?>
    <userPassword>
        <newPassword>{GEOSERVER_ADMIN_PASSWORD}</newPassword>
    </userPassword>"""

    for _cnt in range(1, 29):
        try:
            response = requests.put(
                f"{geoserver_rest_baseurl}/security/self/password",
                data=data,
                headers=headers,
            )
            print(f"Response Code: {response.status_code}")
            if response.status_code == 200:
                print("GeoServer admin password updated SUCCESSFULLY!")
            else:
                logger.warning(
                    f"WARNING: GeoServer admin password *NOT* updated: code [{response.status_code}]"
                )
            break
        except Exception:
            print(f"...waiting for Geoserver to pop-up...{_cnt}")
            time.sleep(2)


def _initialized(ctx):
    print("**************************init file********************************")
    GEOSERVER_DATA_DIR = os.getenv("GEOSERVER_DATA_DIR", "/geoserver_data/data/")
    geoserver_init_lock = Path(GEOSERVER_DATA_DIR) / "geoserver_init.lock"
    ctx.run(f"date > {geoserver_init_lock}")

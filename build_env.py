import argparse
from datetime import datetime
import json
import logging
import os
import random
import re
import string
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def generate_env_file(parser):
    ################################################################
    #######                     Required                    ########
    ################################################################
    parser.add_argument("hostname", help="host name")

    ################################################################
    #######                 Optional                        ########
    ################################################################

    # expected path as a value
    parser.add_argument(
        "-sf",
        "--sample_file",
        help=f"Path of the sample file to use as a template. Default is: {dir_path}/.env.sample",
        default=f"{dir_path}/.env.sample",
    )

    parser.add_argument(
        "-f",
        "--file",
        help="absolute path of the file with the configuration. Note: we expect that the keys of the dictionary have the same name as the CLI params",
    )

    # booleans

    parser.add_argument(
        "--https", action="store_true", default=False, help="If provided, https is used"
    )

    # strings
    parser.add_argument(
        "--email", help="Admin email, this field is required if https is enabled"
    )

    parser.add_argument("--geonodepwd", help="GeoNode admin password")

    parser.add_argument("--geoserverpwd", help="Geoserver admin password")

    parser.add_argument("--pgpwd", help="PostgreSQL password")

    parser.add_argument("--dbpwd", help="GeoNode DB user password")

    parser.add_argument("--geodbpwd", help="Geodatabase user password")

    parser.add_argument("--clientid", help="Oauth2 client id")

    parser.add_argument("--clientsecret", help="Oauth2 client secret")

    parser.add_argument(
        "--env_type",
        help="Development/production or test",
        choices=["prod", "test", "dev"],
        default="prod",
    )

    args = parser.parse_args()
    _sample_file_path = args.sample_file
    # validity checks
    if not os.path.exists(args.sample_file):
        logger.error(f"File does not exists {args.sample_file}")
        raise FileNotFoundError

    if args.file and not os.path.isfile(args.file):
        logger.error(f"File does not exists: {args.file}")
        raise FileNotFoundError

    if args.https and not args.email:
        raise Exception("With HTTPS enabled, the email parameter is required")

    _sample_file = None
    with open(args.sample_file, 'r+') as sample_file:
        _sample_file = sample_file.read()
    
    if not _sample_file:
        raise Exception("Sample file is empty!")

    def _get_vals_to_replace(args):
        _config = ['sample_file', 'file', 'env_type', 'https']
        _jsfile = {}
        if args.file:
            with open(args.file) as _json_file:
                _jsfile = json.load(_json_file)
        _vals_to_replace = {key: val for key, val in vars(args).items() if key not in _config}
        _vals_to_replace["geoserver_ui"] = f"http://{args.hostname}"if not args.https else f"https://{args.hostname}"
        _vals_to_replace["http_host"] = '' if args.https else args.hostname
        _vals_to_replace["letsencrypt_mode"] = 'disabled' if args.https else 'production'
        _vals_to_replace["debug"] = False if args.env_type in ['prod', 'dev'] else True
        return {**_jsfile, **_vals_to_replace}

    for key, val in _get_vals_to_replace(args).items():
        _sample_file = re.sub(
            "{{" + key + "}}",
            lambda _: val or ''.join(random.choice(string.ascii_letters) for _ in range(15)),
            _sample_file
        )

    with open(f"{dir_path}/.env", "w+") as output_env:
        output_env.write(_sample_file)

if __name__ == "__main__":
    logger.info(f"Creation of file started at: {datetime.now()}")
    parser = argparse.ArgumentParser(
        prog="ENV file builder",
        description="Tool for generate environment file automatically. The information can be passed or via CLI or via JSON file ( --file /path/env.json)",
        usage="python build_env.py localhost -f /path/to/json/file.json",
    )
    generate_env_file(parser)
    logger.info(f"Creation of file finished at: {datetime.now()}")

import json
import logging
from os.path import expanduser

from os import environ

import pandas as pd

import requests

from requests.auth import HTTPBasicAuth

import time


# Load credentials
def login():
    try:

        with open(expanduser('brain_credentials.txt')) as f:

            credentials = json.load(f)

    except FileNotFoundError:

        credentials = (environ.get('BRAIN_USERNAME'), environ.get('BRAIN_PASSWORD'))

    # Extract username and password from the list

    username, password = credentials

    # Create a session object (禁用系统代理，避免 VPN 环境下代理失效导致网络异常)
    sess = requests.Session()
    sess.trust_env = False

    # Set up basic authentication
    sess.auth = HTTPBasicAuth(username, password)

    # Send a POST request to the API for authentication
    response = sess.post('https://api.worldquantbrain.com/authentication')
    resp_json = response.json()

    logging.info(f"认证状态码: {response.status_code}")
    logging.info(f"认证响应: {resp_json}")

    if 'rate limit' in str(resp_json.get('message', '')).lower():
        raise SystemExit("API 调用次数已用完 (rate limit exceeded)")

    return sess

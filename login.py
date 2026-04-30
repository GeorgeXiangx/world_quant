import json

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

    # Create a session object

    sess = requests.Session()

    # Set up basic authentication

    sess.auth = HTTPBasicAuth(username, password)

    # Send a POST request to the API for authentication

    response = sess.post('https://api.worldquantbrain.com/authentication')

    # Print response status and content for debugging

    print(response.status_code)

    print(response.json())

    return sess

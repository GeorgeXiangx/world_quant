import json

from os.path import expanduser

from os import environ

import pandas as pd

import requests

from requests.auth import HTTPBasicAuth

import time


## 获取数据集ID为 fundamental6 下的所有数据字段

def get_datafields(
        s,
        instrument_type: str = 'EQUITY',
        region: str = 'USA',
        delay: int = 1,
        universe: str = 'TOP3000',
        dataset_id: str = '',
        data_type: str = 'MATRIX',
        search: str = ''
):
    offset = 0

    datafields_list = []

    while True:
        url_template = "https://api.worldquantbrain.com/data-fields?" + \
                       f"&instrumentType={instrument_type}" + \
                       f"&region={region}&delay={str(delay)}&universe={universe}&dataset.id={dataset_id}&limit=50" + \
                       f"&offset={offset}" + \
                       f"&type={data_type}"

        url_template += (f"&search={search}" if search else "")

        resp = s.get(url_template)

        results = resp.json()

        # print(results)

        if 'results' not in results:

            print(f"Unexpected response: {results}")

            break

        else:

            print(f"Fetched {len(results['results'])} data fields with offset {offset}.")

            datafields_list.append(results['results'])

            if len(results['results']) < 50:
                print("Fetched the last batch of data fields.")

                break

            offset += 50

            # time.sleep(5)

    datafields_list_flat = [item for sublist in datafields_list for item in sublist]

    datafields_df = pd.DataFrame(datafields_list_flat)

    return datafields_df

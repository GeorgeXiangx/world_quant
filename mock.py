import time

import curlify as curlify


def mock(sess, datafields_list):
    alpha_list = []
    group_ops_list = ['group_mean', 'group_neutralize']
    ts_ops_list = ['ts_mean', 'ts_rank']
    days = [63, 126]
    groups = ['market', 'sector', 'industry']

    for datafield in datafields_list:
        for group_ops in group_ops_list:
            for ts_ops in ts_ops_list:
                for day in days:
                    for group in groups:
                        print("正在将如下 Alpha 表达式与 setting 封装")
                        print(f'{group_ops}({ts_ops}({datafield}, {day}), {group})')

                        simulation_data = {
                            'type': 'REGULAR',
                            'settings': {
                                'instrumentType': 'EQUITY',
                                'region': 'USA',
                                'universe': 'TOP3000',
                                'delay': 1,
                                'decay': 0,
                                'neutralization': 'MARKET',
                                'truncation': 0.08,
                                'pasteurization': 'ON',
                                'unitHandling': 'VERIFY',
                                'nanHandling': 'ON',
                                'language': 'FASTEXPR',
                                'visualization': False,
                            },
                            "regular": f'{group_ops}({ts_ops}({datafield}, {day}), {group})'
                        }

                        alpha_list.append(simulation_data)

    for alpha in alpha_list:
        sim_resp = sess.post(
            "https://api.worldquantbrain.com/simulations",
            json=alpha
        )

        try:
            if_success = False
            sim_progress_url = sim_resp.headers['Location']
            print('sim_progress_url = ' + sim_progress_url)
            while True:
                sim_progress_resp = sess.get(sim_progress_url)
                # 打印 GET 请求的 curl 命令
                # print("GET curl 命令:")
                # print(curlify.to_curl(sim_progress_resp.request))
                # print(sim_progress_resp.json())

                if 'status' in sim_progress_resp.json():
                    if sim_progress_resp.json()['status'] == 'ERROR':
                        print('--------- ERROR message = ' + sim_progress_resp.json()['message'])
                    else:
                        print('=========' + sim_progress_resp.json()['status'])
                        if_success = True
                    break

                retry_after_sec = float(sim_progress_resp.headers.get("Retry-After", 0))
                print(f"Retry-After: {retry_after_sec} seconds")
                if retry_after_sec == 0:  # simulation done!
                    break
                time.sleep(retry_after_sec)
            if if_success:
                alpha_id = sim_progress_resp.json()["alpha"]  # the final simulation result
                print(alpha_id)
        except:
            print("no location, sleep for 10 seconds and try next alpha")
            time.sleep(10)

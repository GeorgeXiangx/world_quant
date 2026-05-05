import random

from offical.user.machine_lib import get_datafields, login, process_datafields, first_order_factory, ts_ops, \
    load_task_pool_single, single_simulate


def template_factory(sent_fields, option_fields):
    alpha_list = []
    for sent_field in sent_fields:
        for opt_field in option_fields:
            alpha_list.append("log(1+sigmoid(ts_zscore(%s,30))*sigmoid(ts_zscore(%s,30))" % (sent_field, opt_field))
    return alpha_list


def create_template_factory_instance(s):
    # 模板构建Factory实例

    opt_df = get_datafields(s, dataset_id='option8', region='USA', universe='TOP3000', delay=1)
    opt_fields = opt_df[opt_df['type'] == "MATRIX"]["id"].tolist()
    print(opt_fields)

    sent_df = get_datafields(s, dataset_id='sentiment1', region='USA', universe='TOP3000', delay=1)
    sent_fields = sent_df[sent_df['type'] == "MATRIX"]["id"].tolist()
    print(sent_fields)

    alpha_list = template_factory(sent_fields, opt_fields)
    print(alpha_list)


if __name__ == '__main__':
    s = login()
    # create_template_factory_instance(s)

    # 获取数据字段
    df = get_datafields(s, dataset_id='analyst4', region='USA', universe='TOP3000', delay=1)

    # 4，数据字段预处理
    # 1, matrix, vector 数据类型
    # 2, ts_backfill 回填缺失值，提高数据Coverage
    # 2, winsorize 去极值
    pc_fields = process_datafields(df)
    len(pc_fields)

    # 在factory方法中将数据字段与操作符组装成alpha表达式
    first_order = first_order_factory(pc_fields, ts_ops)
    print(first_order[:10])
    print("生产表达式数量: %s"%len(first_order))

    # 回测前载入
    #1, alpha表达式与初始decay配对
    #2, random shuffle
    #2, Load task pool数据结构
    # 赋予alpha表达式一个初始decay
    init_decay = 4
    fo_alpha_list = []
    for alpha in first_order:
        fo_alpha_list.append((alpha, init_decay))

    # 随机采样快速评估一个数据集的潜力
    random.shuffle(fo_alpha_list)

    print("数量: %s" % len(fo_alpha_list))
    print(fo_alpha_list[:5])

    # Load alphas to task pools
    fo_pools = load_task_pool_single(fo_alpha_list, 3)
    print(fo_pools[0])

    # 回测
    # Simulate First Order
    single_simulate(fo_pools, "SUBINDUSTRY", "USA", "TOP3000", 0)

    # # 筛选Alpha
    # ## get promising alphas to improve in the next order
    # fo_tracker = get_alphas("02-27", "02-28", 1, 0.7, "USA", 100, "track")
    # print(len(fo_tracker))
    #
    # # Prune 剪枝
    # fo_layer = prune(fo_tracker, 'anl4', 5)
    # # 剪枝后数量
    # print(len(fo_layer))


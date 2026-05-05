from user.machine_lib import get_datafields, login


def template_factory(sent_fields, option_fields):
    alpha_list = []
    for sent_field in sent_fields:
        for opt_field in option_fields:
            alpha_list.append("log(1+sigmoid(ts_zscore(%s,30))*sigmoid(ts_zscore(%s,30))" % (sent_field, opt_field))
    return alpha_list


if __name__ == '__main__':
    s = login()

    # 模板构建Factory实例

    opt_df = get_datafields(s, dataset_id='option8', region='USA', universe='TOP3000', delay=1)
    opt_fields = opt_df[opt_df['type'] == "MATRIX"]["id"].tolist()
    print(opt_fields)

    sent_df = get_datafields(s, dataset_id='sentiment1', region='USA', universe='TOP3000', delay=1)
    sent_fields = sent_df[sent_df['type'] == "MATRIX"]["id"].tolist()
    print(sent_fields)

    alpha_list = template_factory(sent_fields, opt_fields)
    print(alpha_list)

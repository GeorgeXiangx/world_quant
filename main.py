from data_set import get_datafields
from login import login
from mock import mock


def get_field(sess):
    fundamental6 = get_datafields(sess, dataset_id='pv13', data_type='GROUP')
    return fundamental6


if __name__ == '__main__':
    sess = login()
    data = get_field(sess)

    # 打印基本信息
    print(f"总行数: {len(data)}")
    print(f"总列数: {len(data.columns)}")
    print(f"\n列名: {data.columns.tolist()}")
    print(f"\n前10行数据:")
    print(data.head(10))

    # 导出到 CSV 文件查看完整数据
    # field.to_csv('./file/fundamental6_data.csv', index=False, encoding='utf-8-sig')
    # print("\n完整数据已保存到 fundamental6_data.csv")

    mock(sess, data)

"""
Alpha 因子回测数据库模块（MySQL 版）
- MySQL 存储每次回测的表达式、设置、MD5、alpha_id 及指标
- MD5(表达式 + 排序后JSON设置) 唯一索引，用于快速去重
- 线程安全：写操作加锁，每个操作使用独立连接

依赖安装：pip install pymysql
"""
import pymysql
import json
import hashlib
import threading
import logging
from datetime import datetime

# ======================== MySQL 配置（按需修改） ========================
MYSQL_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'user':     'root',
    'password': 'Root@1234',              # 请填写你的 MySQL 密码
    'database': 'alpha_simulate', # 库名，需提前创建
    'charset':  'utf8mb4',
}

# 线程锁，保证多线程写入安全
_db_lock = threading.Lock()

# ===== 建表 =====

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS backtest_results (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    label        VARCHAR(255),
    expression   TEXT    NOT NULL,
    settings_json TEXT   NOT NULL,
    md5_hash     VARCHAR(64)  NOT NULL,
    alpha_id     VARCHAR(64),
    status       VARCHAR(32)  DEFAULT 'pending',
    sharpe       DOUBLE,
    fitness      DOUBLE,
    turnover     DOUBLE,
    returns      DOUBLE,
    drawdown     DOUBLE,
    margin       DOUBLE,
    checks_passed  INT DEFAULT 0,
    checks_pending INT DEFAULT 0,
    checks_total   INT DEFAULT 0,
    submittable    INT DEFAULT 0,
    elapsed      DOUBLE,
    decay        INT,
    neutralization VARCHAR(255),
    truncation   DOUBLE,
    universe     VARCHAR(255),
    link         VARCHAR(512),
    run_name     VARCHAR(255),
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_md5_hash (md5_hash),
    INDEX idx_status (status),
    INDEX idx_sharpe (sharpe),
    INDEX idx_run_name (run_name),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# ===== 内部辅助 =====


def _get_connection():
    """获取 MySQL 数据库连接（DictCursor 使查询返回 dict）"""
    return pymysql.connect(
        host=MYSQL_CONFIG['host'],
        port=MYSQL_CONFIG['port'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        charset=MYSQL_CONFIG['charset'],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,  # 手动控制事务
    )


def _execute(conn, sql, params=None):
    """执行 SQL 并返回最后插入行ID（事务由调用方管理）"""
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.lastrowid


def _fetchone(conn, sql, params=None):
    """执行查询并返回单行（dict 或 None）"""
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def _fetchall(conn, sql, params=None):
    """执行查询并返回全部行（list[dict]）"""
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_status ON backtest_results(status);",
    "CREATE INDEX IF NOT EXISTS idx_sharpe ON backtest_results(sharpe);",
    "CREATE INDEX IF NOT EXISTS idx_run_name ON backtest_results(run_name);",
    "CREATE INDEX IF NOT EXISTS idx_created ON backtest_results(created_at);",
]


def init_db():
    """初始化数据库表及索引（幂等，可重复调用）"""
    conn = _get_connection()
    try:
        _execute(conn, CREATE_TABLE_SQL)
        for sql in INDEX_SQLS:
            try:
                _execute(conn, sql)
            except pymysql.err.OperationalError:
                pass  # 旧版 MySQL 不支持 IF NOT EXISTS，忽略已存在报错
        conn.commit()
        logging.info(f"数据库表初始化成功: {MYSQL_CONFIG['database']}.backtest_results")
    finally:
        conn.close()


def _deep_sort_dict(obj):
    """递归排序 dict 所有层级的 key，确保相同内容生成完全一致的 JSON"""
    if isinstance(obj, dict):
        return {k: _deep_sort_dict(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_deep_sort_dict(v) for v in obj]
    return obj


def _dumps_settings(settings):
    """将 settings 序列化为严格排序的 JSON 字符串"""
    sorted_obj = _deep_sort_dict(settings)
    return json.dumps(sorted_obj, sort_keys=True, ensure_ascii=False)


def compute_md5(expression, settings):
    """计算 表达式+设置 的 MD5 哈希（用于去重）"""
    raw = expression + "|" + _dumps_settings(settings)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


# ===== 公共 API =====


def is_already_tested(expression, settings):
    """检查因子是否已经回测过（成功完成的），返回 dict 或 None"""
    md5 = compute_md5(expression, settings)
    conn = _get_connection()
    try:
        return _fetchone(
            conn,
            "SELECT * FROM backtest_results WHERE md5_hash = %s AND status = 'success'",
            (md5,)
        )
    finally:
        conn.close()


def batch_is_already_tested(alphas):
    """批量检查因子是否已回测过（成功完成的）。
    alphas: list of (label, expression, settings)
    返回 dict: md5 -> cached_row (None 表示未回测过)
    一次 MySQL 连接 + 一条 SQL IN 查询，大幅减少连接开销。
    """
    if not alphas:
        return {}
    # 计算所有 MD5，同时保留 label 映射
    md5_to_label = {}
    for label, expr, settings in alphas:
        md5 = compute_md5(expr, settings)
        md5_to_label[md5] = label
    md5_list = list(md5_to_label.keys())
    # 批量查询
    conn = _get_connection()
    try:
        placeholders = ','.join(['%s'] * len(md5_list))
        rows = _fetchall(
            conn,
            f"SELECT * FROM backtest_results WHERE md5_hash IN ({placeholders}) AND status = 'success'",
            tuple(md5_list)
        )
    finally:
        conn.close()
    # 构建 md5 -> row 映射
    result = {md5: None for md5 in md5_list}
    for row in rows:
        result[row['md5_hash']] = row
    return result


def save_result(label, expression, settings, result, run_name=""):
    """保存回测结果到数据库（线程安全），返回 True=新增, False=已存在更新"""
    md5 = compute_md5(expression, settings)

    with _db_lock:
        conn = _get_connection()
        try:
            existing = _fetchone(
                conn,
                "SELECT id FROM backtest_results WHERE md5_hash = %s",
                (md5,)
            )

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if existing:
                _update_record(conn, md5, label, expression, settings, result, run_name, now)
                conn.commit()
                return False
            else:
                _insert_record(conn, md5, label, expression, settings, result, run_name, now)
                conn.commit()
                return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _insert_record(conn, md5, label, expression, settings, result, run_name, now):
    """插入新记录"""
    status, metrics = _extract_metrics(result)
    settings_json = _dumps_settings(settings)

    _execute(conn, """
        INSERT INTO backtest_results
        (label, expression, settings_json, md5_hash, alpha_id, status,
         sharpe, fitness, turnover, returns, drawdown, margin,
         checks_passed, checks_pending, checks_total, submittable,
         elapsed, decay, neutralization, truncation, universe, link,
         run_name, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s)
    """, (
        label, expression, settings_json, md5,
        metrics.get('alpha_id'),
        status,
        metrics.get('sharpe'),
        metrics.get('fitness'),
        metrics.get('turnover'),
        metrics.get('returns'),
        metrics.get('drawdown'),
        metrics.get('margin'),
        metrics.get('checks_passed', 0),
        metrics.get('checks_pending', 0),
        metrics.get('checks_total', 0),
        1 if metrics.get('submittable') else 0,
        metrics.get('elapsed'),
        metrics.get('decay'),
        metrics.get('neutralization'),
        metrics.get('truncation'),
        metrics.get('universe'),
        metrics.get('link'),
        run_name, now, now
    ))


def _update_record(conn, md5, label, expression, settings, result, run_name, now):
    """更新已有记录"""
    status, metrics = _extract_metrics(result)
    settings_json = _dumps_settings(settings)

    _execute(conn, """
        UPDATE backtest_results SET
            label = %s, expression = %s, settings_json = %s,
            alpha_id = %s, status = %s,
            sharpe = %s, fitness = %s, turnover = %s, returns = %s, drawdown = %s, margin = %s,
            checks_passed = %s, checks_pending = %s, checks_total = %s, submittable = %s,
            elapsed = %s, decay = %s, neutralization = %s, truncation = %s, universe = %s, link = %s,
            run_name = %s, updated_at = %s
        WHERE md5_hash = %s
    """, (
        label, expression, settings_json,
        metrics.get('alpha_id'),
        status,
        metrics.get('sharpe'),
        metrics.get('fitness'),
        metrics.get('turnover'),
        metrics.get('returns'),
        metrics.get('drawdown'),
        metrics.get('margin'),
        metrics.get('checks_passed', 0),
        metrics.get('checks_pending', 0),
        metrics.get('checks_total', 0),
        1 if metrics.get('submittable') else 0,
        metrics.get('elapsed'),
        metrics.get('decay'),
        metrics.get('neutralization'),
        metrics.get('truncation'),
        metrics.get('universe'),
        metrics.get('link'),
        run_name, now,
        md5
    ))


def _extract_metrics(result):
    """从 simulate 返回值提取状态和指标，返回 (status, metrics_dict)"""
    if result is None:
        return ('error', {})
    if result.get('timed_out'):
        return ('timeout', {
            'elapsed': result.get('elapsed'),
        })
    return ('success', {
        'alpha_id': result.get('alpha_id'),
        'sharpe': _to_float(result.get('sharpe')),
        'fitness': _to_float(result.get('fitness')),
        'turnover': _to_float(result.get('turnover')),
        'returns': _to_float(result.get('returns')),
        'drawdown': _to_float(result.get('drawdown')),
        'margin': _to_float(result.get('margin')),
        'checks_passed': result.get('checks_passed', 0),
        'checks_pending': result.get('checks_pending', 0),
        'checks_total': result.get('checks_total', 0),
        'submittable': result.get('submittable', False),
        'elapsed': result.get('elapsed'),
        'decay': result.get('decay'),
        'neutralization': result.get('neutralization'),
        'truncation': result.get('truncation'),
        'universe': result.get('universe'),
        'link': result.get('link'),
    })


def _to_float(val):
    """安全转换为 float，'N/A' 等转为 None"""
    if val is None or val == 'N/A' or val == '':
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# ===== 查询 API =====


def get_result_by_md5(expression, settings):
    """根据表达式+设置查询历史回测记录"""
    md5 = compute_md5(expression, settings)
    conn = _get_connection()
    try:
        return _fetchone(conn,
            "SELECT * FROM backtest_results WHERE md5_hash = %s", (md5,)
        )
    finally:
        conn.close()


def get_stats():
    """获取数据库统计信息"""
    conn = _get_connection()
    try:
        total = _fetchone(conn, "SELECT COUNT(*) as cnt FROM backtest_results")['cnt']
        success = _fetchone(conn,
            "SELECT COUNT(*) as cnt FROM backtest_results WHERE status = 'success'"
        )['cnt']
        submittable = _fetchone(conn,
            "SELECT COUNT(*) as cnt FROM backtest_results WHERE submittable = 1"
        )['cnt']
        return {
            'total': total,
            'success': success,
            'submittable': submittable,
            'database': MYSQL_CONFIG['database'],
        }
    finally:
        conn.close()


def top_sharpe(limit=20):
    """查询 Sharpe 最高的记录"""
    conn = _get_connection()
    try:
        return _fetchall(conn,
            "SELECT * FROM backtest_results WHERE status='success' AND sharpe IS NOT NULL "
            "ORDER BY sharpe DESC LIMIT %s", (limit,)
        )
    finally:
        conn.close()


# ===== 自动初始化 =====

# 模块导入时自动检查并初始化数据库
try:
    conn = _get_connection()
    try:
        _fetchone(conn, "SELECT 1 FROM backtest_results LIMIT 1")
    except pymysql.err.ProgrammingError:
        conn.close()
        init_db()
    else:
        conn.close()
except pymysql.err.OperationalError as e:
    logging.error(f"连接 MySQL 失败: {e}")
    logging.error("请检查 MYSQL_CONFIG 配置并确保 MySQL 服务已启动")

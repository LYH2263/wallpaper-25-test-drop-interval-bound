"""幅数（drops）夹逼断言模块。

夹逼定义：对周长 P（米）与幅宽 w（米，夹具给厘米先换米），
分幅入口 app.engines.wallpaper_math.roll_count 返回的 drops 必须满足

        (drops - 1) * w < P <= drops * w

即 drops = ceil(P / w)：少一幅围不住，当前幅数正好盖住。

消息约定（便于一眼分辨失败种类）：
  - "[夹逼失败]"：入口正常返回 drops，但夹逼不等式不成立（或与手算不符）；
  - "[参数拒绝]"：幅宽 <= 0 这种非法入参未被 ValueError 拒绝。
两类消息互不混用；参数拒绝用例只接受 ValueError，绝不允许落到夹逼断言。
"""

import pytest

from app.db import connect as db_connect
from app.engines.wallpaper_math import roll_count
from app.seed import init_db
from app.services import estimate_service
from app.tests.drops_fixtures import (
    DROP_CASES,
    HEIGHT_M,
    MASTER_BED_PERIMETER_M,
    MASTER_BED_WIDTH_CM,
    PATTERN_CM,
    ROLL_LENGTH_M,
    width_cm_to_m,
)

SQUEEZE_FAIL = "[夹逼失败]"
REJECT_FAIL = "[参数拒绝]"


def _squeeze_message(perimeter_m, width_cm, width_m, drops, lower, upper):
    return (
        f"{SQUEEZE_FAIL} 周长={perimeter_m}m 幅宽={width_cm}cm({width_m}m) "
        f"drops={drops}：要求 (drops-1)*幅宽={lower} < 周长={perimeter_m} "
        f"<= drops*幅宽={upper}"
    )


@pytest.mark.parametrize(
    "perimeter_m,width_cm,expected_drops",
    DROP_CASES,
    ids=[f"P={c[0]}m_w={c[1]}cm" for c in DROP_CASES],
)
def test_drops_squeeze(perimeter_m, width_cm, expected_drops):
    """每组夹具走现有分幅入口 roll_count，校验 drops 夹逼。"""
    width_m = width_cm_to_m(width_cm)
    drops = roll_count(
        perimeter_m, HEIGHT_M, width_m, ROLL_LENGTH_M, PATTERN_CM
    )["drops"]
    lower = (drops - 1) * width_m
    upper = drops * width_m

    # 失败时（-s 或失败回显）能直接看到该行周长、幅宽、drops
    print(f"周长={perimeter_m}m 幅宽={width_cm}cm({width_m}m) drops={drops}")

    assert lower < perimeter_m <= upper, _squeeze_message(
        perimeter_m, width_cm, width_m, drops, lower, upper
    )
    # 与夹具表中手算 ceil(P/w) 交叉核对，防止夹逼靠错误 drops“碰巧”成立
    assert drops == expected_drops, (
        f"{SQUEEZE_FAIL} 周长={perimeter_m}m 幅宽={width_cm}cm({width_m}m) "
        f"drops={drops}，与手算期望 {expected_drops} 不符"
    )


@pytest.mark.parametrize("bad_width_cm", [0.0, -53.0], ids=["零幅宽", "负幅宽"])
def test_nonpositive_width_rejected(bad_width_cm):
    """幅宽 <= 0 必须在分幅前被 ValueError 拒绝，不得返回 drops。"""
    perimeter_m = MASTER_BED_PERIMETER_M
    width_m = width_cm_to_m(bad_width_cm)
    print(f"周长={perimeter_m}m 幅宽={bad_width_cm}cm({width_m}m) drops=无(应拒绝)")
    try:
        roll_count(perimeter_m, HEIGHT_M, width_m, ROLL_LENGTH_M, PATTERN_CM)
    except ValueError as exc:
        # 参数拒绝走异常通道，消息不得伪装成夹逼失败
        assert SQUEEZE_FAIL not in str(exc)
        return
    pytest.fail(
        f"{REJECT_FAIL} 周长={perimeter_m}m 幅宽={bad_width_cm}cm({width_m}m) "
        f"drops=? ：幅宽<=0 应抛 ValueError，实际被入口接受"
    )


def _count_calc_runs() -> int:
    conn = db_connect()
    try:
        return conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]
    finally:
        conn.close()


def test_estimate_service_master_bed_plain_dry_run(tmp_path, monkeypatch):
    """经 estimate_service 干算（save=False，不落库）主卧 + 素色53 的烟测。

    使用临时 sqlite 库并重新播种，避免依赖/污染 backend/data/app.db；
    服务层回包中的 drops 同样必须满足夹逼。
    """
    monkeypatch.setattr("app.db.DB_PATH", tmp_path / "test_drops_smoke.db")
    init_db()

    # wall_id=1 主卧一圈(16.0m)，roll_id=1 素色53(0.53m, 10m, 素色)
    assert _count_calc_runs() == 0
    resp = estimate_service.run_estimate(
        wall_id=1, roll_id=1, save=False, note="drops夹逼干算烟测"
    )
    assert resp["run_id"] is None
    assert _count_calc_runs() == 0, "save=False 不应写入 calc_runs"

    perimeter_m = resp["wall"]["perimeter"]
    width_m = resp["roll"]["width"]
    drops = resp["drops"]

    assert perimeter_m == MASTER_BED_PERIMETER_M
    assert width_m == width_cm_to_m(MASTER_BED_WIDTH_CM)

    lower = (drops - 1) * width_m
    upper = drops * width_m
    print(f"周长={perimeter_m}m 幅宽={MASTER_BED_WIDTH_CM}cm({width_m}m) drops={drops}")
    assert lower < perimeter_m <= upper, _squeeze_message(
        perimeter_m, MASTER_BED_WIDTH_CM, width_m, drops, lower, upper
    )
    assert drops == 31

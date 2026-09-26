"""幅数夹逼断言模块：夹具来自 app/tests/drops_fixtures.py。

包含三类用例：
1. 对每组（周长, 幅宽）调用现有分幅入口 roll_count 取 drops，断言夹逼：
       (drops-1) * 幅宽_米 < 周长 <= drops * 幅宽_米
2. 幅宽 <= 0 的参数拒绝用例；失败消息以 [参数拒绝] 开头，与 [夹逼失败] 区分。
3. 经 estimate_service.run_estimate(save=False) 的主卧 + 素色干算烟测（不落库），
   校验服务层回包 drops 同样满足夹逼。
"""

import pytest

from app.engines.wallpaper_math import roll_count
from app.services import estimate_service
from app.repositories import history, rolls, walls
from app.tests.drops_fixtures import DROP_CASES, INVALID_WIDTH_CASES

# 夹逼只与周长、幅宽有关；其余分幅入口入参取固定常规值。
_HEIGHT_M = 2.7
_ROLL_LENGTH_M = 10.0
_PATTERN_CM = 0.0

# 米级浮点容差：兜住 30.0 / 0.6 这类整除边界的二进制舍入误差。
_EPS = 1e-9


def _drops_via_engine(perimeter_m: float, width_cm: float) -> int:
    """调用现有分幅入口；夹具幅宽是厘米，这里先换成米。"""
    width_m = float(width_cm) / 100.0
    return roll_count(
        perimeter_m, _HEIGHT_M, width_m, _ROLL_LENGTH_M, _PATTERN_CM
    )["drops"]


def _assert_squeeze(perimeter_m: float, width_m: float, drops: int, where: str) -> None:
    """断言 (drops-1)*W < P <= drops*W。

    任何一条不满足都以 [夹逼失败] 前缀报出，并在消息里打印该行周长、幅宽、drops。
    """
    lower = (drops - 1) * width_m
    upper = drops * width_m
    line = f"位置={where} | 周长={perimeter_m}m, 幅宽={width_m}m, drops={drops}"
    assert lower < perimeter_m + _EPS, (
        f"[夹逼失败] {line} | 下界 (drops-1)*幅宽={lower} 应严格小于周长"
    )
    assert perimeter_m <= upper + _EPS, (
        f"[夹逼失败] {line} | 上界 drops*幅宽={upper} 应不小于周长"
    )


@pytest.mark.parametrize("case", DROP_CASES, ids=[c.name for c in DROP_CASES])
def test_drops_squeeze(case):
    drops = _drops_via_engine(case.perimeter_m, case.width_cm)
    print(f"\n{case.name}: 周长={case.perimeter_m}m, 幅宽={case.width_cm}cm, drops={drops}")
    width_m = case.width_cm / 100.0
    _assert_squeeze(case.perimeter_m, width_m, drops, where=case.name)


@pytest.mark.parametrize(
    "case", INVALID_WIDTH_CASES, ids=[c.name for c in INVALID_WIDTH_CASES]
)
def test_nonpositive_width_rejected(case):
    """幅宽 <= 0 必须被入口拒绝；报错消息走 [参数拒绝]，不与夹逼失败混淆。"""
    line = f"位置={case.name} | 周长={case.perimeter_m}m, 幅宽={case.width_cm}cm"
    with pytest.raises(ValueError) as excinfo:
        _drops_via_engine(case.perimeter_m, case.width_cm)
    assert "invalid roll size" in str(excinfo.value), (
        f"[参数拒绝] {line} | 期望 ValueError('invalid roll size')，实际为: {excinfo.value!r}"
    )


@pytest.fixture()
def seeded_temp_db(monkeypatch, tmp_path):
    """把 DATA_DIR / DB_PATH 指到临时目录并播种，保证干算烟测不碰开发库。"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    from app import config as app_config
    from app import db as app_db
    from app import seed

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    db_file = data_dir / "app.db"
    # app.db 在导入时 `from app.config import DB_PATH` 绑定了旧值，两处都要改。
    monkeypatch.setattr(app_config, "DB_PATH", db_file)
    monkeypatch.setattr(app_db, "DB_PATH", db_file)
    seed.init_db()
    return db_file


def test_master_bed_plain_dry_run_via_service(seeded_temp_db):
    """主卧一圈 + 素色53，经 estimate_service 干算（save=False），不落库且 drops 满足夹逼。"""
    wall = next(w for w in walls.list_walls() if w["name"] == "主卧一圈")
    roll = next(r for r in rolls.list_rolls() if r["name"] == "素色53")
    assert wall["perimeter"] == 16.0
    assert roll["width"] == 0.53

    runs_before = len(history.list_runs())
    result = estimate_service.run_estimate(wall["id"], roll["id"], False, "干算烟测-不落库")

    # 干算：不返回 run_id，calc_runs 行数不变。
    assert result["run_id"] is None, "[参数拒绝/落库异常] 干算不应返回 run_id"
    runs_after = len(history.list_runs())
    assert runs_after == runs_before, (
        f"[落库异常] save=False 不应写 calc_runs：before={runs_before}, after={runs_after}"
    )

    drops = result["drops"]
    print(
        f"\nestimate-service 主卧+素色(干算): "
        f"周长={wall['perimeter']}m, 幅宽={roll['width']}m, drops={drops}"
    )
    _assert_squeeze(
        wall["perimeter"], roll["width"], drops, where="estimate_service:主卧一圈+素色53(干算)"
    )

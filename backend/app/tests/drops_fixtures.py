"""幅数夹逼测试夹具表（只放数据，不含断言，pytest 不直接收集）。

夹逼关系：对周长 P（米）与幅宽 W（米），分幅入口给出的 drops 应满足
    (drops - 1) * W < P <= drops * W
本模块的幅宽一律以 **厘米** 记录，断言侧先 / 100 换成米再调用入口。

夹具来源（短说明）
------------------
1. master-seed  —— 来自 app/seed.py：walls 种子行「主卧一圈」perimeter=16.0 m，
   幅宽取 rolls 种子行「素色53」(53 cm)。
2. 其余六组均为 **手写值**，人工挑选以覆盖不同分幅边界：
   - hand-short  ：短墙一圈，数值与 app/tests/test_calc.py 的手写短墙一致；
   - hand-exact50：50 cm 幅宽，周长被整除（恰 20 幅）；
   - hand-wide60 ：60 cm 宽幅大圈，整除但浮点上界有误差，靠容差判定；
   - hand-tight  ：贴边情形，26 幅仅比周长多出约 0.01 m；
   - hand-mini   ：极小周长，恰 5 幅（浮点除法边界，压引擎 1e-9 修正）；
   - hand-70     ：70 cm 宽幅小圈，非整除。
另附 INVALID_WIDTH_CASES：幅宽 <= 0 的拒绝用例（手写）。
"""

from typing import List, NamedTuple


class DropCase(NamedTuple):
    name: str
    perimeter_m: float
    width_cm: float
    source: str


# 不少于六组：1 组主卧种子 + 6 组手写值。
DROP_CASES: List[DropCase] = [
    DropCase(
        "master-seed",
        16.0,
        53,
        "种子：app/seed.py「主卧一圈」perimeter=16.0 +「素色53」53cm",
    ),
    DropCase(
        "hand-short",
        4.0,
        53,
        "手写：短墙一圈，与 test_calc.py 短墙同值",
    ),
    DropCase(
        "hand-exact50",
        10.0,
        50,
        "手写：50cm 幅宽整除，drops 恰为 20",
    ),
    DropCase(
        "hand-wide60",
        30.0,
        60,
        "手写：60cm 宽幅大圈整除（drops=50），浮点上界需容差",
    ),
    DropCase(
        "hand-tight",
        13.77,
        53,
        "手写：贴边，drops=26，26*0.53=13.78 仅余约 0.01m",
    ),
    DropCase(
        "hand-mini",
        2.65,
        53,
        "手写：极小周长，恰 5 幅（浮点除法边界）",
    ),
    DropCase(
        "hand-70",
        8.0,
        70,
        "手写：70cm 宽幅小圈，非整除（drops=12）",
    ),
]


class InvalidWidthCase(NamedTuple):
    name: str
    perimeter_m: float
    width_cm: float
    source: str


# 幅宽 <= 0 必须被分幅入口拒绝（ValueError）。
INVALID_WIDTH_CASES: List[InvalidWidthCase] = [
    InvalidWidthCase("zero-width", 16.0, 0, "手写：零幅宽"),
    InvalidWidthCase("negative-width", 16.0, -53, "手写：负幅宽"),
]

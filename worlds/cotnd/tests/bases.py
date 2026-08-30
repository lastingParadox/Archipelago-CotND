from typing import ClassVar

from test.bases import WorldTestBase
from worlds.cotnd import CotNDWorld

class CotNDTestBase(WorldTestBase):
    game = "Crypt of the NecroDancer"
    player: ClassVar[int] = 1
    world: CotNDWorld # pyright: ignore[reportIncompatibleVariableOverride]

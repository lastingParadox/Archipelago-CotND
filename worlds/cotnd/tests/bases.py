from typing import ClassVar

from test.bases import WorldTestBase


class CotNDTestBase(WorldTestBase):
    game = "Crypt of the NecroDancer"
    player: ClassVar[int] = 1

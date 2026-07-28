import random
import uuid
from decimal import Decimal

from api.schemas.simulation import SpriteAppearance, VirtualCustomer


class CustomerGenerator:
    NAMES = (
        "Mia",
        "Noah",
        "Ava",
        "Leo",
        "Sophie",
        "Jack",
        "Emma",
        "Liam",
    )
    SKIN_COLORS = ("light", "medium", "dark")
    HAIR_COLORS = ("black", "brown", "blonde", "red")
    SHIRT_COLORS = ("blue", "green", "red", "yellow", "purple")
    PANTS_COLORS = ("navy", "black", "brown", "grey")
    ACCESSORIES = ("none", "cap", "glasses", "headphones")

    def __init__(self, randomizer=None):
        self.randomizer = randomizer or random.Random()

    def generate(self) -> VirtualCustomer:
        budget_cents = self.randomizer.randint(100, 2000)
        return VirtualCustomer(
            customer_id=f"CUST-{uuid.uuid4().hex[:8].upper()}",
            name=self.randomizer.choice(self.NAMES),
            sprite=SpriteAppearance(
                skin=self.randomizer.choice(self.SKIN_COLORS),
                hair=self.randomizer.choice(self.HAIR_COLORS),
                shirt=self.randomizer.choice(self.SHIRT_COLORS),
                pants=self.randomizer.choice(self.PANTS_COLORS),
                accessory=self.randomizer.choice(self.ACCESSORIES),
            ),
            budget=Decimal(budget_cents) / Decimal("100"),
        )

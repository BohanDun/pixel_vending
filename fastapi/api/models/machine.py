from sqlalchemy import Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


machine_product_association = Table(
    "machine_products",
    Base.metadata,
    Column("machine_id", Integer, ForeignKey("machines.id")),
    Column("product_id", Integer, ForeignKey("products.id")),
    Column("quantity", Integer, nullable=False, default=0),
    UniqueConstraint("machine_id", "product_id", name="uq_machine_product"),
)


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    description = Column(String, index=True)
    products = relationship(
        "Product",
        secondary=machine_product_association,
        back_populates="machines",
    )

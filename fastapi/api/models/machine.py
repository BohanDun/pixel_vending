from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


DEFAULT_MACHINE_PRODUCT_CAPACITY = 20


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    description = Column(String, index=True)
    machine_products = relationship(
        "MachineProduct",
        back_populates="machine",
        cascade="all, delete-orphan",
    )


class MachineProduct(Base):
    __tablename__ = "machine_products"

    machine_id = Column(Integer, ForeignKey("machines.id"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    quantity = Column(Integer, nullable=False, default=0)
    capacity = Column(
        Integer,
        nullable=False,
        default=DEFAULT_MACHINE_PRODUCT_CAPACITY,
        server_default=str(DEFAULT_MACHINE_PRODUCT_CAPACITY),
    )
    low_stock_threshold = Column(
        Integer, nullable=False, default=5, server_default="5"
    )
    auto_restock_enabled = Column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    last_restocked_at = Column(DateTime, nullable=True)

    machine = relationship("Machine", back_populates="machine_products")
    product = relationship("Product", back_populates="machine_products")

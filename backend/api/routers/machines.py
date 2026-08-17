from typing import Optional
from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy.orm import joinedload

from api.models import Machine, MachineProduct, Product
from api.models.machine import DEFAULT_MACHINE_PRODUCT_CAPACITY
from api.deps import db_dependency, user_dependency
from api.schemas.machine import (
    MachineCreate,
    MachineProductQuantity,
    MachineProductSettings,
)

router = APIRouter(
    prefix="/machines",
    tags=["machines"],
)

MAX_MACHINES_PER_USER = 4
MACHINE_LIMIT_MESSAGE = "sorry, no availabe space"


def get_machine_product(db, machine_id: int, product_id: int):
    return (
        db.query(MachineProduct)
        .filter(
            MachineProduct.machine_id == machine_id,
            MachineProduct.product_id == product_id,
        )
        .first()
    )

def ensure_enough_warehouse_quantity(product: Product, quantity: int):
    if quantity > product.quantity:
        raise HTTPException(
            status_code=400,
            detail="Not enough warehouse quantity",
        )

def ensure_enough_machine_capacity(
    machine_product: MachineProduct,
    quantity_to_add: int,
):
    capacity = (
        machine_product.capacity
        if machine_product.capacity is not None
        else DEFAULT_MACHINE_PRODUCT_CAPACITY
    )
    current_quantity = machine_product.quantity or 0
    remaining_capacity = capacity - current_quantity
    if quantity_to_add > remaining_capacity:
        raise HTTPException(
            status_code=400,
            detail="Quantity exceeds machine product capacity",
        )

def serialize_machine(machine: Machine):
    return {
        "id": machine.id,
        "user_id": machine.user_id,
        "name": machine.name,
        "description": machine.description,
        "products": [
            {
                "id": machine_product.product.id,
                "user_id": machine_product.product.user_id,
                "name": machine_product.product.name,
                "description": machine_product.product.description,
                "quantity": machine_product.product.quantity,
                "price": machine_product.product.price,
                "machine_quantity": machine_product.quantity,
                "capacity": machine_product.capacity,
                "low_stock_threshold": machine_product.low_stock_threshold,
                "auto_restock_enabled": machine_product.auto_restock_enabled,
                "last_restocked_at": machine_product.last_restocked_at,
            }
            for machine_product in machine.machine_products
        ],
    }

@router.get("/")
def get_machines(db: db_dependency, user: user_dependency):
    machines = (
        db.query(Machine)
        .options(
            joinedload(Machine.machine_products).joinedload(MachineProduct.product)
        )
        .filter(Machine.user_id == user.get("id"))
        .all()
    )
    return [serialize_machine(machine) for machine in machines]

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_machine(db: db_dependency, user: user_dependency, payload: MachineCreate):
    machine_count = (
        db.query(Machine)
        .filter(Machine.user_id == user.get("id"))
        .count()
    )
    if machine_count >= MAX_MACHINES_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MACHINE_LIMIT_MESSAGE,
        )

    db_machine = Machine(
        name=payload.name,
        description=payload.description,
        user_id=user.get("id"),
    )

    selected_products = {}
    ids = list(dict.fromkeys(payload.products or []))
    if ids:
        products = (
            db.query(Product)
            .filter(Product.id.in_(ids), Product.user_id == user.get("id"))
            .all()
        )
        selected_products.update({product.id: product for product in products})

    if payload.product_names:
        names = list(
            dict.fromkeys(
                n.strip() for n in payload.product_names if n and n.strip()
            )
        )
        if names:
            existing = (
                db.query(Product)
                .filter(Product.user_id == user.get("id"), Product.name.in_(names))
                .all()
            )
            by_name = {product.name: product for product in existing}
            for nm in names:
                product = by_name.get(nm)
                if product is None:
                    product = Product(name=nm, user_id=user.get("id"))
                    db.add(product)
                    db.flush()
                    by_name[nm] = product
                selected_products[product.id] = product

    db_machine.machine_products = [
        MachineProduct(product=product) for product in selected_products.values()
    ]

    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)

    db_machine = (
        db.query(Machine)
        .options(
            joinedload(Machine.machine_products).joinedload(MachineProduct.product)
        )
        .filter(Machine.id == db_machine.id)
        .first()
    )
    return serialize_machine(db_machine)

@router.post("/{machine_id}/products/{product_id}")
def add_product_to_machine(
    db: db_dependency,
    user: user_dependency,
    machine_id: int,
    product_id: int,
    payload: Optional[MachineProductQuantity] = None,
):
    db_machine = (
        db.query(Machine)
        .filter(Machine.id == machine_id, Machine.user_id == user.get("id"))
        .first()
    )

    if db_machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    db_product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == user.get("id"))
        .first()
    )

    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    quantity = payload.quantity if payload else 0
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")

    ensure_enough_warehouse_quantity(db_product, quantity)

    machine_product = get_machine_product(db, machine_id, product_id)
    if machine_product is None:
        machine_product = MachineProduct(
            machine_id=db_machine.id,
            product_id=db_product.id,
            quantity=0,
            capacity=DEFAULT_MACHINE_PRODUCT_CAPACITY,
        )

    ensure_enough_machine_capacity(machine_product, quantity)

    db.add(machine_product)
    db_product.quantity -= quantity
    machine_product.quantity += quantity
    db.commit()
    db.refresh(db_machine)

    return serialize_machine(db_machine)

@router.put("/{machine_id}/products/{product_id}/settings")
def update_machine_product_settings(
    db: db_dependency,
    user: user_dependency,
    machine_id: int,
    product_id: int,
    payload: MachineProductSettings,
):
    db_machine = (
        db.query(Machine)
        .filter(Machine.id == machine_id, Machine.user_id == user.get("id"))
        .first()
    )
    if db_machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    machine_product = get_machine_product(db, machine_id, product_id)
    if machine_product is None:
        raise HTTPException(status_code=404, detail="Product not found in machine")

    if payload.low_stock_threshold >= payload.capacity:
        raise HTTPException(
            status_code=400,
            detail="Low stock threshold must be less than capacity",
        )

    if machine_product.quantity > payload.capacity:
        raise HTTPException(
            status_code=400,
            detail="Capacity cannot be less than current machine stock",
        )

    machine_product.capacity = payload.capacity
    machine_product.low_stock_threshold = payload.low_stock_threshold
    machine_product.auto_restock_enabled = payload.auto_restock_enabled
    db.commit()
    db.refresh(db_machine)
    return serialize_machine(db_machine)

@router.put("/{machine_id}/products/{product_id}/quantity")
def update_machine_product_quantity(
    db: db_dependency,
    user: user_dependency,
    machine_id: int,
    product_id: int,
    payload: MachineProductQuantity,
):
    db_machine = (
        db.query(Machine)
        .options(
            joinedload(Machine.machine_products).joinedload(MachineProduct.product)
        )
        .filter(Machine.id == machine_id, Machine.user_id == user.get("id"))
        .first()
    )

    if db_machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    db_product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == user.get("id"))
        .first()
    )

    machine_product = get_machine_product(db, machine_id, product_id)
    if db_product is None or machine_product is None:
        raise HTTPException(status_code=404, detail="Product not found in machine")

    quantity_delta = payload.quantity - machine_product.quantity

    if quantity_delta > 0:
        ensure_enough_warehouse_quantity(db_product, quantity_delta)
        ensure_enough_machine_capacity(machine_product, quantity_delta)
        db_product.quantity -= quantity_delta
    elif quantity_delta < 0:
        db_product.quantity += abs(quantity_delta)

    machine_product.quantity = payload.quantity
    db.commit()
    db.refresh(db_machine)

    return serialize_machine(db_machine)

@router.post("/{machine_id}/products/{product_id}/delete-quantity")
def delete_machine_product_quantity(
    db: db_dependency,
    user: user_dependency,
    machine_id: int,
    product_id: int,
    payload: MachineProductQuantity,
):
    db_machine = (
        db.query(Machine)
        .options(
            joinedload(Machine.machine_products).joinedload(MachineProduct.product)
        )
        .filter(Machine.id == machine_id, Machine.user_id == user.get("id"))
        .first()
    )

    if db_machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    db_product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == user.get("id"))
        .first()
    )

    machine_product = get_machine_product(db, machine_id, product_id)
    if db_product is None or machine_product is None:
        raise HTTPException(status_code=404, detail="Product not found in machine")

    if payload.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero",
        )

    if payload.quantity > machine_product.quantity:
        raise HTTPException(
            status_code=400,
            detail="Not enough machine stock",
        )

    if payload.quantity == machine_product.quantity:
        db.delete(machine_product)
    else:
        machine_product.quantity -= payload.quantity

    db.commit()
    db.refresh(db_machine)

    return serialize_machine(db_machine)

@router.post("/{machine_id}/products/{product_id}/put-back")
def put_machine_product_quantity_back(
    db: db_dependency,
    user: user_dependency,
    machine_id: int,
    product_id: int,
    payload: MachineProductQuantity,
):
    db_machine = (
        db.query(Machine)
        .options(
            joinedload(Machine.machine_products).joinedload(MachineProduct.product)
        )
        .filter(Machine.id == machine_id, Machine.user_id == user.get("id"))
        .first()
    )

    if db_machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    db_product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == user.get("id"))
        .first()
    )

    machine_product = get_machine_product(db, machine_id, product_id)
    if db_product is None or machine_product is None:
        raise HTTPException(status_code=404, detail="Product not found in machine")

    quantity_to_return = min(payload.quantity, machine_product.quantity)

    if quantity_to_return <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")

    db_product.quantity += quantity_to_return

    if quantity_to_return >= machine_product.quantity:
        db.delete(machine_product)
    else:
        machine_product.quantity -= quantity_to_return

    db.commit()
    db.refresh(db_machine)

    return serialize_machine(db_machine)

@router.delete("/{machine_id}/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_product_from_machine(db: db_dependency, user: user_dependency, machine_id: int, product_id: int,):
    db_machine = (
        db.query(Machine)
        .filter(Machine.id == machine_id, Machine.user_id == user.get("id"))
        .first()
    )

    if db_machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    db_product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == user.get("id"))
        .first()
    )

    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    machine_product = get_machine_product(db, machine_id, product_id)
    if machine_product is not None:
        db_product.quantity += machine_product.quantity
        db.delete(machine_product)
        db.commit()


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(db: db_dependency, user: user_dependency, machine_id: int):
    db_machine = (
        db.query(Machine)
        .options(
            joinedload(Machine.machine_products).joinedload(MachineProduct.product)
        )
        .filter(Machine.id == machine_id, Machine.user_id == user.get("id"))
        .first()
    )
    if db_machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    for machine_product in db_machine.machine_products:
        if machine_product.product is not None:
            machine_product.product.quantity += machine_product.quantity

    db.delete(db_machine)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

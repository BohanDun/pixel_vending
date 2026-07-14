from typing import Optional
from fastapi import APIRouter, status, HTTPException
from sqlalchemy.orm import joinedload

from api.models import Product, Machine, machine_product_association
from api.deps import db_dependency, user_dependency
from api.schemas.machine import MachineCreate, MachineProductQuantity

router = APIRouter(
    prefix="/machines",
    tags=["machines"],
)

def get_machine_product_quantity(db, machine_id: int, product_id: int):
    row = (
        db.query(machine_product_association.c.quantity)
        .filter(
            machine_product_association.c.machine_id == machine_id,
            machine_product_association.c.product_id == product_id,
        )
        .first()
    )
    return row.quantity if row else 0

def ensure_enough_warehouse_quantity(product: Product, quantity: int):
    if quantity > product.quantity:
        raise HTTPException(
            status_code=400,
            detail="Not enough warehouse quantity",
        )

def serialize_machine(db, machine: Machine):
    product_quantities = {
        row.product_id: row.quantity
        for row in db.query(
            machine_product_association.c.product_id,
            machine_product_association.c.quantity,
        )
        .filter(machine_product_association.c.machine_id == machine.id)
        .all()
    }

    return {
        "id": machine.id,
        "user_id": machine.user_id,
        "name": machine.name,
        "description": machine.description,
        "products": [
            {
                "id": product.id,
                "user_id": product.user_id,
                "name": product.name,
                "description": product.description,
                "quantity": product.quantity,
                "price": product.price,
                "machine_quantity": product_quantities.get(product.id, 0),
            }
            for product in machine.products
        ],
    }

@router.get("/")
def get_machines(db: db_dependency, user: user_dependency):
    machines = (
        db.query(Machine)
        .options(joinedload(Machine.products))
        .filter(Machine.user_id == user.get("id"))
        .all()
    )
    return [serialize_machine(db, machine) for machine in machines]

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_machine(db: db_dependency, user: user_dependency, payload: MachineCreate):
    db_machine = Machine(
        name=payload.name,
        description=payload.description,
        user_id=user.get("id"),
    )

    ids = list(dict.fromkeys(payload.products or []))
    if ids:
        products = (
            db.query(Product)
            .filter(Product.id.in_(ids), Product.user_id == user.get("id"))
            .all()
        )
        db_machine.products.extend(products)

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
                if product not in db_machine.products:
                    db_machine.products.append(product)

    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)

    db_machine = (
        db.query(Machine)
        .options(joinedload(Machine.products))
        .filter(Machine.id == db_machine.id)
        .first()
    )
    return serialize_machine(db, db_machine)

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

    if db_product not in db_machine.products:
        db_machine.products.append(db_product)
        db.flush()

    current_quantity = get_machine_product_quantity(db, machine_id, product_id)
    db_product.quantity -= quantity

    db.execute(
        machine_product_association.update()
        .where(
            machine_product_association.c.machine_id == machine_id,
            machine_product_association.c.product_id == product_id,
        )
        .values(quantity=current_quantity + quantity)
    )
    db.commit()
    db.refresh(db_machine)

    return serialize_machine(db, db_machine)

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
        .options(joinedload(Machine.products))
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

    if db_product is None or db_product not in db_machine.products:
        raise HTTPException(status_code=404, detail="Product not found in machine")

    current_quantity = get_machine_product_quantity(db, machine_id, product_id)
    quantity_delta = payload.quantity - current_quantity

    if quantity_delta > 0:
        ensure_enough_warehouse_quantity(db_product, quantity_delta)
        db_product.quantity -= quantity_delta

    db.execute(
        machine_product_association.update()
        .where(
            machine_product_association.c.machine_id == machine_id,
            machine_product_association.c.product_id == product_id,
        )
        .values(quantity=payload.quantity)
    )
    db.commit()
    db.refresh(db_machine)

    return serialize_machine(db, db_machine)

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
        .options(joinedload(Machine.products))
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

    if db_product is None or db_product not in db_machine.products:
        raise HTTPException(status_code=404, detail="Product not found in machine")

    current_quantity = get_machine_product_quantity(db, machine_id, product_id)

    if payload.quantity >= current_quantity:
        db_machine.products.remove(db_product)
    else:
        db.execute(
            machine_product_association.update()
            .where(
                machine_product_association.c.machine_id == machine_id,
                machine_product_association.c.product_id == product_id,
            )
            .values(quantity=current_quantity - payload.quantity)
        )

    db.commit()
    db.refresh(db_machine)

    return serialize_machine(db, db_machine)

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
        .options(joinedload(Machine.products))
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

    if db_product is None or db_product not in db_machine.products:
        raise HTTPException(status_code=404, detail="Product not found in machine")

    current_quantity = get_machine_product_quantity(db, machine_id, product_id)
    quantity_to_return = min(payload.quantity, current_quantity)

    if quantity_to_return <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")

    db_product.quantity += quantity_to_return

    if quantity_to_return >= current_quantity:
        db_machine.products.remove(db_product)
    else:
        db.execute(
            machine_product_association.update()
            .where(
                machine_product_association.c.machine_id == machine_id,
                machine_product_association.c.product_id == product_id,
            )
            .values(quantity=current_quantity - quantity_to_return)
        )

    db.commit()
    db.refresh(db_machine)

    return serialize_machine(db, db_machine)

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

    if db_product in db_machine.products:
        db_product.quantity += get_machine_product_quantity(db, machine_id, product_id)
        db_machine.products.remove(db_product)
        db.commit()


@router.delete("/{machine_id}")
def delete_machine(db: db_dependency, user: user_dependency, machine_id: int):
    db_machine = (
        db.query(Machine)
        .filter(Machine.id == machine_id, Machine.user_id == user.get("id"))
        .first()
    )
    if db_machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    product_quantities = (
        db.query(
            machine_product_association.c.product_id,
            machine_product_association.c.quantity,
        )
        .filter(machine_product_association.c.machine_id == machine_id)
        .all()
    )

    for product_quantity in product_quantities:
        db_product = (
            db.query(Product)
            .filter(
                Product.id == product_quantity.product_id,
                Product.user_id == user.get("id"),
            )
            .first()
        )
        if db_product is not None:
            db_product.quantity += product_quantity.quantity

    db.execute(
        machine_product_association.delete().where(
            machine_product_association.c.machine_id == machine_id
        )
    )
    db.delete(db_machine)
    db.commit()
    return db_machine

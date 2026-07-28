from fastapi import APIRouter, status, HTTPException
from api.models import Machine, MachineProduct, Product
from api.deps import db_dependency, user_dependency
from api.schemas.product import ProductCreate, ProductPriceUpdate, ProductQuantityChange

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/{product_id}")
def get_product(db: db_dependency, user: user_dependency, product_id: int):
    return (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == user.get("id"))
        .first()
    )

@router.get("/")
def get_products(db: db_dependency, user: user_dependency):
    products = db.query(Product).filter(Product.user_id == user.get("id")).all()
    product_ids = [product.id for product in products]
    machine_quantities_by_product = {product_id: [] for product_id in product_ids}

    if product_ids:
        rows = (
            db.query(
                MachineProduct.product_id,
                Machine.id.label("machine_id"),
                Machine.name.label("machine_name"),
                MachineProduct.quantity,
            )
            .join(Machine, Machine.id == MachineProduct.machine_id)
            .filter(
                MachineProduct.product_id.in_(product_ids),
                Machine.user_id == user.get("id"),
            )
            .all()
        )

        for row in rows:
            machine_quantities_by_product[row.product_id].append(
                {
                    "machine_id": row.machine_id,
                    "machine_name": row.machine_name,
                    "quantity": row.quantity,
                }
            )

    return [
        {
            "id": product.id,
            "user_id": product.user_id,
            "name": product.name,
            "description": product.description,
            "quantity": product.quantity,
            "price": product.price,
            "machine_quantities": machine_quantities_by_product[product.id],
            "machine_quantity_total": sum(
                item["quantity"] for item in machine_quantities_by_product[product.id]
            ),
        }
        for product in products
    ]

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_product(db: db_dependency, user: user_dependency, product: ProductCreate):
    db_product = Product(**product.model_dump(), user_id=user.get("id"))
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.put("/{product_id}/price")
def update_product_price(
    db: db_dependency,
    user: user_dependency,
    product_id: int,
    payload: ProductPriceUpdate,
):
    db_product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == user.get("id"))
        .first()
    )

    if db_product is None:
        raise HTTPException(status_code=404, detail="Not found")

    db_product.price = payload.price
    db.commit()
    db.refresh(db_product)
    return db_product

@router.post("/{product_id}/restock")
def restock_product(
    db: db_dependency,
    user: user_dependency,
    product_id: int,
    payload: ProductQuantityChange,
):
    db_product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == user.get("id"))
        .first()
    )

    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.quantity += payload.quantity
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(db: db_dependency, user: user_dependency, product_id: int):
    db_product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.user_id == user.get("id"))
        .first()
    )
    if db_product is None:
        raise HTTPException(status_code=404, detail="Not found")
    db.query(MachineProduct).filter(
        MachineProduct.product_id == db_product.id
    ).delete(synchronize_session=False)
    db.delete(db_product)
    db.commit()

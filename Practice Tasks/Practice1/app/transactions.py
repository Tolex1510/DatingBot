from decimal import Decimal

from sqlalchemy.orm import Session

from .models import Customer, Order, OrderItem, Product


def place_order(
    session: Session,
    customer_id: int,
    items: list[dict],  # [{"product_id": int, "quantity": int}, ...]
) -> Order:
    """Сценарий 1: размещение заказа в одной транзакции."""
    with session.begin():
        order = Order(customer_id=customer_id, total_amount=Decimal("0"))
        session.add(order)
        session.flush()  # получаем order.id

        total = Decimal("0")
        for item in items:
            product = session.get(Product, item["product_id"])
            if product is None:
                raise ValueError(f"Product {item['product_id']} not found")

            subtotal = product.price * item["quantity"]
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item["quantity"],
                subtotal=subtotal,
            )
            session.add(order_item)
            total += subtotal

        order.total_amount = total

    return order


def update_customer_email(
    session: Session,
    customer_id: int,
    new_email: str,
) -> Customer:
    """Сценарий 2: атомарное обновление email клиента."""
    with session.begin():
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise ValueError(f"Customer {customer_id} not found")
        customer.email = new_email

    return customer


def add_product(
    session: Session,
    product_name: str,
    price: Decimal,
) -> Product:
    """Сценарий 3: атомарное добавление нового продукта."""
    with session.begin():
        product = Product(product_name=product_name, price=price)
        session.add(product)

    return product

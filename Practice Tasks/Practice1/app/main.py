import time
from decimal import Decimal

from sqlalchemy import text

from .database import Base, SessionLocal, engine
from .models import Customer, Product
from .transactions import add_product, place_order, update_customer_email


def wait_for_db(retries: int = 10, delay: float = 2.0) -> None:
    """Ожидание готовности PostgreSQL."""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("DB is ready.")
            return
        except Exception:
            print(f"Waiting for DB... attempt {attempt}/{retries}")
            time.sleep(delay)
    raise RuntimeError("Database is not available")


def seed_data() -> None:
    """Заполнение тестовыми данными."""
    session = SessionLocal()
    with session.begin():
        customer = Customer(
            first_name="Ivan",
            last_name="Petrov",
            email="ivan@example.com",
        )
        session.add(customer)

        products = [
            Product(product_name="Laptop", price=Decimal("999.99")),
            Product(product_name="Mouse", price=Decimal("29.99")),
            Product(product_name="Keyboard", price=Decimal("79.99")),
        ]
        session.add_all(products)

    print("Seed data created.")
    session.close()


def run_scenarios() -> None:
    """Запуск всех трёх сценариев."""

    # --- Сценарий 1: размещение заказа ---
    print("\n=== Сценарий 1: Размещение заказа ===")
    session = SessionLocal()
    order = place_order(
        session,
        customer_id=1,
        items=[
            {"product_id": 1, "quantity": 1},  # Laptop
            {"product_id": 2, "quantity": 2},  # Mouse x2
        ],
    )
    print(f"Создан заказ: {order}")
    for item in order.items:
        print(f"  {item}")
    session.close()

    # --- Сценарий 2: обновление email ---
    print("\n=== Сценарий 2: Обновление email ===")
    session = SessionLocal()
    customer = update_customer_email(session, customer_id=1, new_email="ivan.new@example.com")
    print(f"Обновлён клиент: {customer}")
    session.close()

    # --- Сценарий 3: добавление продукта ---
    print("\n=== Сценарий 3: Добавление продукта ===")
    session = SessionLocal()
    product = add_product(session, product_name="Monitor", price=Decimal("349.99"))
    print(f"Добавлен продукт: {product}")
    session.close()

    print("\nВсе сценарии выполнены успешно.")


def main() -> None:
    wait_for_db()
    Base.metadata.create_all(engine)
    print("Tables created.")

    seed_data()
    run_scenarios()


if __name__ == "__main__":
    main()

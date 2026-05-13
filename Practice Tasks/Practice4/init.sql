-- Создание тестовой таблицы
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS products CASCADE;

CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    balance INTEGER NOT NULL CHECK (balance >= 0),
    version INTEGER DEFAULT 0
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    stock INTEGER NOT NULL CHECK (stock >= 0)
);

-- Вставка тестовых данных
INSERT INTO accounts (id, name, balance) VALUES 
(1, 'Alice', 1000),
(2, 'Bob', 500),
(3, 'Charlie', 750);

INSERT INTO products (id, name, stock) VALUES 
(1, 'Laptop', 10),
(2, 'Mouse', 25);

-- Создание индексов для производительности
CREATE INDEX idx_accounts_balance ON accounts(balance);
CREATE INDEX idx_products_stock ON products(stock);

-- Вывод начального состояния
SELECT 'Initial data loaded' as status;
SELECT * FROM accounts;
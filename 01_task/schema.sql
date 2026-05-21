
-- OLTP VRSTVA

CREATE TABLE categories (
    category_id  SERIAL PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    parent_id    INT REFERENCES categories(category_id),
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE products (
    product_id   SERIAL PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    price        DECIMAL(10,2) NOT NULL,
    description  TEXT,
    is_available BOOLEAN DEFAULT TRUE,
    category_id  INT REFERENCES categories(category_id),
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE customers (
    customer_id   SERIAL PRIMARY KEY,
    full_name     VARCHAR(255) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    registered_at DATE NOT NULL
);

CREATE TABLE addresses (
    address_id   SERIAL PRIMARY KEY,
    customer_id  INT NOT NULL REFERENCES customers(customer_id),
    street       VARCHAR(255),
    city         VARCHAR(100),
    postal_code  VARCHAR(20),
    region       VARCHAR(100),
    country_code VARCHAR(10),
    is_default   BOOLEAN DEFAULT FALSE
);

CREATE TABLE orders (
    order_id    SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id),
    address_id  INT REFERENCES addresses(address_id),
    ordered_at  TIMESTAMP NOT NULL,
    status      VARCHAR(50) CHECK (status IN (
                    'pending','confirmed','shipped',
                    'delivered','cancelled','returned'))
);

CREATE TABLE order_items (
    item_id    SERIAL PRIMARY KEY,
    order_id   INT NOT NULL REFERENCES orders(order_id),
    product_id INT NOT NULL REFERENCES products(product_id),
    quantity   INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL,
    unit_cost  DECIMAL(10,2)
);

CREATE TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,
    order_id       INT NOT NULL REFERENCES orders(order_id),
    transacted_at  TIMESTAMP NOT NULL,
    payment_method VARCHAR(50),
    amount         DECIMAL(10,2) NOT NULL,
    status         VARCHAR(50)
);

-- ANALYTICKÁ VRSTVA — STAR SCHEMA

CREATE TABLE dim_date (
    date_id    INT PRIMARY KEY,
    full_date  DATE,
    year       INT,
    quarter    INT,
    month      INT,
    week       INT,
    is_weekend BOOLEAN
);

CREATE TABLE dim_product (
    product_key  SERIAL PRIMARY KEY,
    product_id   INT,
    product_name VARCHAR(255),
    category     VARCHAR(255),
    -- SCD Type 2: zachytáva historické zmeny cien
    valid_from   DATE,
    valid_to     DATE,
    is_current   BOOLEAN DEFAULT TRUE
);

CREATE TABLE dim_geography (
    geo_key      SERIAL PRIMARY KEY,
    postal_code  VARCHAR(20),
    city         VARCHAR(100),
    region       VARCHAR(100),
    country_code VARCHAR(10)
);

CREATE TABLE fact_sales (
    sale_id     SERIAL PRIMARY KEY,
    date_id     INT REFERENCES dim_date(date_id),
    product_key INT REFERENCES dim_product(product_key),
    geo_key     INT REFERENCES dim_geography(geo_key),
    order_id    INT,
    quantity    INT,
    unit_price  DECIMAL(10,2),
    unit_cost   DECIMAL(10,2),
    revenue     DECIMAL(10,2),
    margin      DECIMAL(10,2)
);

-- INDEXY pre výkon

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_created  ON orders(ordered_at);
CREATE INDEX idx_items_order     ON order_items(order_id);
CREATE INDEX idx_items_product   ON order_items(product_id);
CREATE INDEX idx_fact_date       ON fact_sales(date_id);
CREATE INDEX idx_fact_product    ON fact_sales(product_key);
CREATE INDEX idx_fact_geo        ON fact_sales(geo_key);
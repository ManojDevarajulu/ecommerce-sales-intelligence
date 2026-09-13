-- ============================================================================
-- E-Commerce Sales Intelligence Platform - Relational Database Schema
-- File: sql/01_schema.sql
-- ============================================================================

-- Ensure required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- ----------------------------------------------------------------------------
-- 1. Customers Table (Dimension)
-- ----------------------------------------------------------------------------
-- Stores 25,000 unique customer profiles with demographic and geographic data.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    customer_id                 VARCHAR(32) PRIMARY KEY,
    customer_name               VARCHAR(255) NOT NULL,
    customer_age                INTEGER CHECK (customer_age >= 0 AND customer_age <= 120),
    gender                      VARCHAR(32),
    customer_segment            VARCHAR(64),
    customer_city               VARCHAR(128),
    customer_state              VARCHAR(128),
    customer_country            VARCHAR(128),
    region                      VARCHAR(64) NOT NULL,
    customer_postal_code        VARCHAR(32),
    customer_acquisition_cost   NUMERIC(10, 2) DEFAULT 0.00,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for frequent customer filtering and regional segmentation
CREATE INDEX idx_customers_region ON customers(region);
CREATE INDEX idx_customers_segment ON customers(customer_segment);

-- ----------------------------------------------------------------------------
-- 2. Products Table (Dimension)
-- ----------------------------------------------------------------------------
-- Stores 1,175 distinct product SKUs across 15 retail categories.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS products CASCADE;

CREATE TABLE products (
    product_id              VARCHAR(32) PRIMARY KEY,
    product_name            VARCHAR(255) NOT NULL,
    product_category        VARCHAR(128) NOT NULL,
    product_subcategory     VARCHAR(128),
    brand                   VARCHAR(128),
    supplier                VARCHAR(128),
    unit_price              NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    product_cost            NUMERIC(12, 2) NOT NULL CHECK (product_cost >= 0),
    product_rating          NUMERIC(3, 2) CHECK (product_rating >= 0.0 AND product_rating <= 5.0),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for category-level analytics and brand filtering
CREATE INDEX idx_products_category ON products(product_category);
CREATE INDEX idx_products_brand ON products(brand);

-- ----------------------------------------------------------------------------
-- 3. Orders Table (Financial Fact Table)
-- ----------------------------------------------------------------------------
-- Stores 138,116 commercial transactions with order-level financial metrics,
-- fulfillment states, and customer snapshot attributes at order time.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS orders CASCADE;

CREATE TABLE orders (
    order_id                    VARCHAR(32) PRIMARY KEY,
    customer_id                 VARCHAR(32) NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    order_date                  DATE NOT NULL,
    order_time                  TIME,
    order_status                VARCHAR(64) NOT NULL,
    sales_channel               VARCHAR(64),
    customer_type               VARCHAR(64),
    region                      VARCHAR(64),
    payment_method              VARCHAR(64),
    payment_status              VARCHAR(64),
    currency                    VARCHAR(16) DEFAULT 'USD',
    shipping_method             VARCHAR(64),
    warehouse                   VARCHAR(64),
    delivery_days               NUMERIC(6, 2), -- NULL for unfulfilled/cancelled/returned orders
    estimated_delivery_days     NUMERIC(6, 2),
    delivery_status             VARCHAR(64) NOT NULL,
    return_status               VARCHAR(64), -- 'Returned' or NULL
    return_reason               VARCHAR(255),
    marketing_channel           VARCHAR(64),
    campaign_name               VARCHAR(128),
    coupon_code                 VARCHAR(64),
    loyalty_points_earned       INTEGER DEFAULT 0,
    loyalty_points_redeemed     INTEGER DEFAULT 0,
    quantity                    INTEGER NOT NULL CHECK (quantity > 0),
    gross_sales                 NUMERIC(12, 2) NOT NULL,
    discount_amount             NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_amount                  NUMERIC(12, 2) DEFAULT 0.00,
    shipping_cost               NUMERIC(12, 2) DEFAULT 0.00,
    net_sales                   NUMERIC(12, 2) NOT NULL,
    product_cost                NUMERIC(12, 2) NOT NULL,
    profit                      NUMERIC(12, 2) NOT NULL,
    profit_margin_percentage    NUMERIC(6, 2),
    customer_lifetime_value     NUMERIC(12, 2),
    is_repeat_customer          BOOLEAN DEFAULT FALSE,
    customer_order_count        INTEGER DEFAULT 1,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for time-series reporting, customer lookup, and analytical slicing
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_order_status ON orders(order_status);
CREATE INDEX idx_orders_delivery_status ON orders(delivery_status);
CREATE INDEX idx_orders_return_status ON orders(return_status);
CREATE INDEX idx_orders_region ON orders(region);
CREATE INDEX idx_orders_sales_channel ON orders(sales_channel);
CREATE INDEX idx_orders_marketing_channel ON orders(marketing_channel);

-- ----------------------------------------------------------------------------
-- 4. Order Items Table (Transaction Line Items)
-- ----------------------------------------------------------------------------
-- Stores 397,569 line-item records (~2.88 items per basket) linking orders
-- to individual catalog SKUs with unit-level pricing and discounts.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS order_items CASCADE;

CREATE TABLE order_items (
    order_item_id           BIGSERIAL PRIMARY KEY,
    order_id                VARCHAR(32) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id              VARCHAR(32) NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    quantity                INTEGER NOT NULL CHECK (quantity > 0),
    unit_price              NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    discount_percentage     NUMERIC(6, 4) DEFAULT 0.0000,
    discount_amount         NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    gross_sales             NUMERIC(12, 2) NOT NULL,
    tax_amount              NUMERIC(12, 2) DEFAULT 0.00,
    shipping_cost           NUMERIC(12, 2) DEFAULT 0.00,
    net_sales               NUMERIC(12, 2) NOT NULL,
    product_cost            NUMERIC(12, 2) NOT NULL,
    profit                  NUMERIC(12, 2) NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for basket decomposition and SKU revenue analytics
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_order_items_composite ON order_items(order_id, product_id);

-- ----------------------------------------------------------------------------
-- 5. Ratings / Reviews Table (Entity Normalization)
-- ----------------------------------------------------------------------------
-- Normalized review entity storing 113,559 post-delivery ratings and sentiments.
-- Decoupled from orders to eliminate sparse nulls for the 24,557 unfulfilled orders.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS ratings CASCADE;

CREATE TABLE ratings (
    rating_id               BIGSERIAL PRIMARY KEY,
    order_id                VARCHAR(32) NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
    customer_id             VARCHAR(32) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    rating                  NUMERIC(3, 1) NOT NULL CHECK (rating >= 1.0 AND rating <= 5.0),
    review_sentiment        VARCHAR(32),
    customer_review         TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for customer satisfaction and sentiment aggregation
CREATE INDEX idx_ratings_order_id ON ratings(order_id);
CREATE INDEX idx_ratings_customer_id ON ratings(customer_id);
CREATE INDEX idx_ratings_rating ON ratings(rating);
CREATE INDEX idx_ratings_sentiment ON ratings(review_sentiment);

-- ----------------------------------------------------------------------------
-- 6. RAG Chunks Table (Vector Store Foundation)
-- ----------------------------------------------------------------------------
-- Vector storage for the RAG knowledge base (rag/ingest.py). One row per
-- `##` section of a rag/documents/*.md file.
-- Embedding dimension = 1024, matching EMBEDDING_MODEL=qwen3-embedding:0.6b
-- (Qwen3-Embedding-0.6B) served by Ollama - see .env.example. Note that
-- pgvector's HNSW index rejects columns wider than 2000 dimensions, which
-- is why the larger Qwen3-Embedding sizes (2560/4096) are not an option
-- here without giving up the index.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS rag_chunks CASCADE;

CREATE TABLE rag_chunks (
    id                      BIGSERIAL PRIMARY KEY,
    doc_title               VARCHAR(255) NOT NULL,
    section_title           VARCHAR(255),
    chunk_text              TEXT NOT NULL,
    embedding               vector(1024),
    metadata                JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- HNSW index for sub-millisecond approximate cosine similarity search
CREATE INDEX idx_rag_chunks_embedding ON rag_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_rag_chunks_doc_title ON rag_chunks(doc_title);




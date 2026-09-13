# Entity-Relationship Diagram

Schema: [`sql/01_schema.sql`](../sql/01_schema.sql). The design notes at the
bottom of this file cover the two choices worth explaining: why `ratings` is
split out of `orders`, and why `orders` keeps only point-in-time customer
snapshot fields.

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    CUSTOMERS ||--o{ RATINGS : writes
    ORDERS    ||--o{ ORDER_ITEMS : contains
    ORDERS    ||--o| RATINGS : "rated by (0 or 1)"
    PRODUCTS  ||--o{ ORDER_ITEMS : "sold via"

    CUSTOMERS {
        varchar customer_id PK
        varchar customer_name
        int customer_age
        varchar gender
        varchar customer_segment
        varchar customer_city
        varchar customer_state
        varchar customer_country
        varchar region
        varchar customer_postal_code
        numeric customer_acquisition_cost
    }

    PRODUCTS {
        varchar product_id PK
        varchar product_name
        varchar product_category
        varchar product_subcategory
        varchar brand
        varchar supplier
        numeric unit_price
        numeric product_cost
        numeric product_rating
    }

    ORDERS {
        varchar order_id PK
        varchar customer_id FK
        date order_date
        time order_time
        varchar order_status
        varchar sales_channel
        varchar customer_type
        varchar region
        varchar payment_method
        varchar payment_status
        varchar currency
        varchar shipping_method
        varchar warehouse
        numeric delivery_days
        numeric estimated_delivery_days
        varchar delivery_status
        varchar return_status
        varchar return_reason
        varchar marketing_channel
        varchar campaign_name
        varchar coupon_code
        int loyalty_points_earned
        int loyalty_points_redeemed
        int quantity
        numeric gross_sales
        numeric discount_amount
        numeric tax_amount
        numeric shipping_cost
        numeric net_sales
        numeric product_cost
        numeric profit
        numeric profit_margin_percentage
        numeric customer_lifetime_value
        boolean is_repeat_customer
        int customer_order_count
    }

    ORDER_ITEMS {
        bigint order_item_id PK
        varchar order_id FK
        varchar product_id FK
        int quantity
        numeric unit_price
        numeric discount_percentage
        numeric discount_amount
        numeric gross_sales
        numeric tax_amount
        numeric shipping_cost
        numeric net_sales
        numeric product_cost
        numeric profit
    }

    RATINGS {
        bigint rating_id PK
        varchar order_id FK "UNIQUE"
        varchar customer_id FK
        numeric rating
        varchar review_sentiment
        text customer_review
    }

    RAG_CHUNKS {
        bigint id PK
        varchar doc_title
        varchar section_title
        text chunk_text
        vector embedding "1024-dim, qwen3-embedding:0.6b (Ollama)"
        jsonb metadata
    }
```

`rag_chunks` has no FK relationship to the transactional tables —
it stores embedded chunks of the markdown knowledge-base documents generated
from this data, not the rows themselves, so it's omitted from the
relationship edges above.

## Design notes

- **`orders` vs `customers`**: `orders` deliberately keeps only a handful of
  customer fields that could in principle change between orders
  (`customer_type`, `region`, `customer_lifetime_value`,
  `customer_order_count`) rather than re-deriving them via a join every time
  — the rest of the demographic data (name, age, gender, address) lives only
  in `customers`. In this dataset these snapshot fields turned out to be
  100% constant per customer (verified independently), so this is a
  forward-looking modeling choice rather than one this dataset's data
  actually exercises.
- **`ratings` split from `orders`**: 24,557 of 138,116 orders (17.8%) were
  never delivered and so have no rating — splitting the table keeps `orders`
  fully dense and avoids a sparse nullable block of 3 columns on every row.
- **`order_items` is the only place with product-level revenue**: `orders`
  carries order-level totals; category/product breakdowns (Q2, Q5, Q8) must
  go through `order_items` → `products`.

CREATE TABLE customers (
    id NVARCHAR(64) NOT NULL,
    username NVARCHAR(40),
    identity_card_no NVARCHAR(12) NOT NULL,
    address NVARCHAR(120) NOT NULL,

    CONSTRAINT PK_customers PRIMARY KEY (id),
    CONSTRAINT UQ_customers_identity_card UNIQUE (identity_card_no)
);
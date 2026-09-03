CREATE TABLE customers (
    id NVARCHAR(64) NOT NULL,
    username NVARCHAR(40),
    identity_number NVARCHAR(12) NOT NULL,
    address NVARCHAR(120) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL

    CONSTRAINT PK_customers PRIMARY KEY (id),
    CONSTRAINT UQ_customers_identity_number UNIQUE (identity_number)
);
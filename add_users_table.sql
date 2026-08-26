CREATE TABLE users (
    id NVARCHAR(64) NOT NULL,
    username NVARCHAR(32) NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,

    CONSTRAINT PK_users PRIMARY KEY (id),
    CONSTRAINT UQ_users_username UNIQUE (username)
);
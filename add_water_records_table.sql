USE water_meter;
GO

CREATE TABLE water_records (
    id INT IDENTITY(1,1) NOT NULL,
    customer_id NVARCHAR(64) NOT NULL,
    image_path NVARCHAR(256) NOT NULL,
    record_time DATETIMEOFFSET NOT NULL
        DEFAULT SYSDATETIMEOFFSET(),
    result FLOAT NOT NULL,
    ability INT,
    coordinates_path NVARCHAR(256),
    photographer_id NVARCHAR(64) NOT NULL,

    CONSTRAINT PK_water_records
        PRIMARY KEY (id),

    CONSTRAINT FK_water_records_customers
        FOREIGN KEY (customer_id)
        REFERENCES customers(id),

    CONSTRAINT FK_water_records_photographers
        FOREIGN KEY (photographer_id)
        REFERENCES users(id)
);
GO
USE water_meter;
GO

CREATE TABLE water_records (
    id INT IDENTITY(1,1) NOT NULL,
    user_id NVARCHAR(64) NOT NULL,
    image_path NVARCHAR(256) NOT NULL,
    record_time DATETIMEOFFSET NOT NULL
        DEFAULT SYSDATETIMEOFFSET(),
    result FLOAT NOT NULL,
    ability INT,
    coordinates_path NVARCHAR(256),

    CONSTRAINT PK_water_records
        PRIMARY KEY (id),

    CONSTRAINT FK_water_records_users
        FOREIGN KEY (user_id)
        REFERENCES users(id)
);
GO
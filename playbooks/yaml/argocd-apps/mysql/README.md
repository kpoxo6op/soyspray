# MySQL

MySQL deployment using Bitnami Helm chart.

## Configuration

- Uses Longhorn for persistence
- Creates a test database and user
- Minimal resource allocation for testing

## Access

Left Ear

```sh
kubectl port-forward -n mysql svc/mysql 3306:3306
```

right ear

```sh
mysql -h 127.0.0.1 -u testuser -p'testpass' testdb

SHOW DATABASES;
+--------------------+
| Database           |
+--------------------+
| information_schema |
| performance_schema |
| testdb             |
+--------------------+
```

## Generate Data

create a large table

```sql
CREATE TABLE test_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    random_string VARCHAR(255),
    random_text TEXT,
    random_number INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Create a stored procedure to generate data

```sql
DELIMITER //
CREATE PROCEDURE generate_test_data(IN num_rows INT)
BEGIN
    DECLARE i INT DEFAULT 0;

    -- Create a loop to insert data
    WHILE i < num_rows DO
        INSERT INTO test_data (random_string, random_text, random_number)
        VALUES (
            CONCAT('String-', FLOOR(RAND() * 1000000)),
            REPEAT(CONCAT('Lorem ipsum dolor sit amet ', FLOOR(RAND() * 1000000)), 50),
            FLOOR(RAND() * 1000000)
        );
        SET i = i + 1;

        -- Commit every 1000 rows to prevent transaction log from growing too large
        IF i % 1000 = 0 THEN
            COMMIT;
        END IF;
    END WHILE;
END //
DELIMITER ;
```

Call the procedure to generate approximately 1GB of data

```sql
CALL generate_test_data(100000);
```

Drop the table to start over

```sql
DROP TABLE IF EXISTS test_data;
```

## Check Volume in Longhorn GUI

Started at 394Mi size, now growing as `generate_test_data` is running.

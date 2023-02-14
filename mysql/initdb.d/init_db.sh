#!/bin/bash

mysql -u root --password="$DB_PASSWORD"  << EOF
USE ${MYSQL_DATABASE};
GRANT ALL PRIVILEGES ON  pintalk.* TO 'root';
EOF
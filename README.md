*TEMPE_CTRL*
========

Designed to run on __Amazon Web Services Lambda__

### `.env` file

```
CONTROL_URL="..."
CONTROL_LOGIN="..."
CONTROL_PASSWORD="..."

MEASURE_URL="..."
MEASURE_LOGIN="..."
MEASURE_PASSWORD="..."

DB_USER="..."
DB_NAME="..."
DB_PASSWORD="..."
DB_PORT="..."
DB_HOST="..."

KEY_1="..."
KEY_2="..."
```

`CONTROL_` keys refer to the temperature control platform

`MEASURE_` keys refer to the temperature measurement platform

`DB_` keys should point to a designated PostgresSQL Database

`API_KEY_1` in *TEMPE_UI* equal to sha256 hash of `KEY_1` in *TEMPE_CTRL*
`KEY_2` in *TEMPE_CTRL* equal to sha256 hash of `API_KEY_2` in *TEMPE_UI*
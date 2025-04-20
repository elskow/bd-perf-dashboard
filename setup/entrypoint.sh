#!/bin/bash
set -e

# Start Odoo in the background
/entrypoint.sh odoo &
ODOO_PID=$!

# Wait for Odoo to become available
echo "Waiting for Odoo to start (this may take a minute)..."
for i in $(seq 1 60); do
    if curl -s http://localhost:8069/ > /dev/null; then
        echo "Odoo is up and running!"
        break
    fi
    echo "Attempt $i/60: Waiting for Odoo..."
    sleep 5
done

# Run the database setup script
echo "Running database setup script..."
python3 /setup/setup_odoo.py --url http://localhost:8069

# Keep the container running by waiting for the Odoo process
wait $ODOO_PID

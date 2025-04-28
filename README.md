punya chika
iya


# How to get started

1. Run the odoo instance using [docker compose](https://docs.docker.com/compose/)
    ```
    docker compose up -d
    ```

2. Check is the odoo instance already up(?)
    ```
    docker compose logs
    ```

    the instance indicate running successfully when the log already said
    `Odoo setup completed successfully!`

3. If the odoo instance already up, we can start feeding the web by running the script under `scripts`
    ```
    python scripts/generate_dummy_data.py  --count {number_of_leads} --year {date_year} --csv scripts/assets/company-list.csv --meetings {number_meetings}
    ```

    - `number_of_leads` : Number of leads to generate
    - `date_year` : Simulation year
    - `meetings` : Total number of meetings to generate


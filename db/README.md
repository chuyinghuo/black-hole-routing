## Background Information
- We're using SqlAlchemy as the ORM (uses Python)

## Setup
- Add a .env file in the db directory, with `DATABASE_URL="postgresql://<your username>:<your password>*@localhost:5432/<your database name>"`
-   The .gitignore file in the db directory ensures this information is not tracked by git.

For the next steps, make sure you're running commands from inside the db directory so all the paths can be resolved. 
- Run `pip install -r requirements.txt`. Whether psycopg2 or psycopg2-binary works may be machine dependent; right now the requirement is psycopg2-binary but change to psycopg2 if the binary version is throwing errors.
- Run `setup.py` to apply the database schema (defined in models.py)
- Anytime the schema changes, data generation must be changed to match the schema. After generating new data, the team must run setup.py again to apply both the schema & data changes.
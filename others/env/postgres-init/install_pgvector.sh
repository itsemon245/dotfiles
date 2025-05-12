#!/bin/bash

set -e

# Install required dependencies
apt-get update
apt-get install -y build-essential postgresql-server-dev-${PG_MAJOR} git

# Clone the pgvector repository
git clone https://github.com/pgvector/pgvector.git
cd pgvector

# Compile and install the extension
make
make install

# Enable the extension in the database
psql -U postgres -d global_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

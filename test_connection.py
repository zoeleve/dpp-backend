import os
import socket
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
host = os.getenv("POSTGRES_SERVER")

print(f"🔍 Diagnostics for host: {host}")

# 1. Test DNS Resolution
try:
    ip_address = socket.gethostbyname(host)
    print(f"✅ DNS Resolution Successful: {host} -> {ip_address}")
except socket.gaierror as e:
    print(f"❌ DNS Resolution Failed: {e}")
    print("   -> Your computer cannot find the IP address for this Supabase project.")
    print("   -> Try flushing your DNS or checking your internet connection.")
    exit(1)

# 2. Test TCP Connection (Port 5432)
try:
    sock = socket.create_connection((host, 5432), timeout=5)
    print("✅ TCP Connection to Port 5432 Successful!")
    sock.close()
except Exception as e:
    print(f"❌ TCP Connection Failed: {e}")
    print("   -> The server is reachable via DNS, but the port is blocked.")
    print("   -> Check Firewalls or VPN settings.")
    exit(1)

# 3. Test Database Login
print("🔄 Attempting Database Login...")
if db_url and db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

try:
    conn = psycopg2.connect(db_url)
    print("✅ Database Login Successful!")
    conn.close()
except psycopg2.OperationalError as e:
    print(f"❌ Database Login Failed: {e}")
except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")

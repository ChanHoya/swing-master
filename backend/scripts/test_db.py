"""단일 주소 DB 연결 테스트 지정"""
import asyncio
import sys
from urllib.parse import urlparse, unquote
import asyncpg

# .env 파싱
env = {}
with open(".env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

raw_url = env.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
parsed = urlparse(raw_url)
host = parsed.hostname
port = parsed.port or 5432
database = parsed.path.lstrip("/")
user = unquote(parsed.username or "")
password = unquote(parsed.password or "")

async def main():
    print(f"🔌 {host}:{port} 에 연결 시도 중...")
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            ssl="require",
            timeout=10,
        )
        ver = await conn.fetchval("SELECT version()")
        await conn.close()
        print(f"✅ 성공! PostgreSQL: {ver[:60]}")
    except Exception as e:
        print(f"❌ 실패: {type(e).__name__}: {e}")
        sys.exit(1)

asyncio.run(main())

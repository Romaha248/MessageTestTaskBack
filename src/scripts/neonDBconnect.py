import asyncio
from sqlalchemy import text
from src.database.dbcore import engine


async def async_main():
    async with engine.connect() as conn:
        result = await conn.execute(text("select 'hello world from neon'"))
        print(result.fetchall())
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(async_main())

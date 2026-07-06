from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./donna_core.db"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    # Import the Base and schemas together cleanly to attach metadata
    from backend.app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
import datetime
import aiosqlite
import certifi
from config import DB_PATH, MONGO_URI

# Check if MongoDB is enabled
USE_MONGO = bool(MONGO_URI and MONGO_URI.strip())

if USE_MONGO:
    from motor.motor_asyncio import AsyncIOMotorClient
    # Use certifi SSL CA bundle to prevent TLS handshake errors on Render/Linux
    mongo_client = AsyncIOMotorClient(
        MONGO_URI,
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000
    )
    mongo_db = mongo_client.swiggy_bot
else:
    mongo_client = None
    mongo_db = None

def get_db():
    return aiosqlite.connect(DB_PATH)

async def init_db():
    if USE_MONGO:
        # Create MongoDB Indexes
        await mongo_db.users.create_index("user_id", unique=True)
        await mongo_db.links.create_index("swiggy_link", unique=True)
        await mongo_db.links.create_index("user_id")
        await mongo_db.link_distributions.create_index([("user_id", 1), ("link_id", 1)], unique=True)
        await mongo_db.bot_settings.create_index("key", unique=True)

        # Default settings
        if not await mongo_db.bot_settings.find_one({"key": "bot_active"}):
            await mongo_db.bot_settings.insert_one({"key": "bot_active", "value": "1"})
        if not await mongo_db.bot_settings.find_one({"key": "links_enabled"}):
            await mongo_db.bot_settings.insert_one({"key": "links_enabled", "value": "1"})
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    swiggy_name TEXT,
                    swiggy_link TEXT UNIQUE,
                    is_restricted INTEGER DEFAULT 0,
                    can_receive_links INTEGER DEFAULT 1,
                    last_links_request_at TEXT,
                    created_at TEXT
                )
            """)

            # Migrate existing DBs that don't have the new column yet
            try:
                await db.execute("ALTER TABLE users ADD COLUMN can_receive_links INTEGER DEFAULT 1")
                await db.commit()
            except Exception:
                pass  # Column already exists

            await db.execute("""
                CREATE TABLE IF NOT EXISTS links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    swiggy_name TEXT,
                    swiggy_link TEXT UNIQUE,
                    received_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS link_distributions (
                    user_id INTEGER,
                    link_id INTEGER,
                    distributed_at TEXT,
                    PRIMARY KEY (user_id, link_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (link_id) REFERENCES links(id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('bot_active', '1')")
            await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('links_enabled', '1')")
            await db.commit()

async def get_setting(key: str, default: str = "1") -> str:
    if USE_MONGO:
        doc = await mongo_db.bot_settings.find_one({"key": key})
        return doc["value"] if doc else default
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row["value"] if row else default

async def set_setting(key: str, value: str):
    if USE_MONGO:
        await mongo_db.bot_settings.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))
            await db.commit()

async def get_user(user_id: int):
    if USE_MONGO:
        return await mongo_db.users.find_one({"user_id": user_id})
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

async def link_exists(swiggy_link: str) -> bool:
    if USE_MONGO:
        doc = await mongo_db.links.find_one({"swiggy_link": swiggy_link})
        return doc is not None
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id FROM links WHERE swiggy_link = ?", (swiggy_link,)) as cursor:
                row = await cursor.fetchone()
                return row is not None

async def user_has_link(user_id: int) -> bool:
    if USE_MONGO:
        doc = await mongo_db.links.find_one({"user_id": user_id})
        return doc is not None
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id FROM links WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row is not None

async def register_user_and_link(user_id: int, username: str, first_name: str, swiggy_name: str, swiggy_link: str):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if USE_MONGO:
        user_doc = await mongo_db.users.find_one({"user_id": user_id})
        is_restricted = user_doc["is_restricted"] if user_doc and "is_restricted" in user_doc else 0
        
        await mongo_db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "swiggy_name": swiggy_name,
                "swiggy_link": swiggy_link,
                "is_restricted": is_restricted,
                "created_at": now
            }},
            upsert=True
        )

        await mongo_db.links.update_one(
            {"swiggy_link": swiggy_link},
            {"$set": {
                "user_id": user_id,
                "swiggy_name": swiggy_name,
                "swiggy_link": swiggy_link,
                "created_at": now
            },
            "$setOnInsert": {
                "received_count": 0
            }},
            upsert=True
        )
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            await db.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name, swiggy_name, swiggy_link, is_restricted, can_receive_links, created_at)
                VALUES (?, ?, ?, ?, ?,
                    COALESCE((SELECT is_restricted FROM users WHERE user_id = ?), 0),
                    COALESCE((SELECT can_receive_links FROM users WHERE user_id = ?), 1),
                    ?)
            """, (user_id, username, first_name, swiggy_name, swiggy_link, user_id, user_id, now))

            await db.execute("""
                INSERT OR REPLACE INTO links (user_id, swiggy_name, swiggy_link, created_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, swiggy_name, swiggy_link, now))

            await db.commit()

async def restrict_user(user_id: int, status: int):
    if USE_MONGO:
        await mongo_db.users.update_one({"user_id": user_id}, {"$set": {"is_restricted": status}})
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            await db.execute("UPDATE users SET is_restricted = ? WHERE user_id = ?", (status, user_id))
            await db.commit()

async def set_user_can_receive_links(user_id: int, status: int):
    """Toggle whether this user can receive links (1 = yes, 0 = no)."""
    if USE_MONGO:
        await mongo_db.users.update_one({"user_id": user_id}, {"$set": {"can_receive_links": status}})
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            await db.execute("UPDATE users SET can_receive_links = ? WHERE user_id = ?", (status, user_id))
            await db.commit()

async def add_bulk_links(raw_links: list, admin_user_id: int):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    added_count = 0
    dup_count = 0
    invalid_count = 0

    for link in raw_links:
        link_str = str(link).strip()
        if not link_str:
            continue
            
        if not (link_str.startswith("http://") or link_str.startswith("https://")):
            invalid_count += 1
            continue

        if await link_exists(link_str):
            dup_count += 1
            continue

        if USE_MONGO:
            try:
                await mongo_db.links.insert_one({
                    "user_id": admin_user_id,
                    "swiggy_name": "Admin Upload",
                    "swiggy_link": link_str,
                    "received_count": 0,
                    "created_at": now
                })
                added_count += 1
            except Exception:
                dup_count += 1
        else:
            async with get_db() as db:
                try:
                    await db.execute("""
                        INSERT INTO links (user_id, swiggy_name, swiggy_link, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (admin_user_id, "Admin Upload", link_str, now))
                    await db.commit()
                    added_count += 1
                except Exception:
                    dup_count += 1

    return added_count, dup_count, invalid_count

async def get_available_links_for_user(user_id: int, limit: int = 50):
    if USE_MONGO:
        # Get list of link_ids user already received
        received_docs = await mongo_db.link_distributions.find({"user_id": user_id}).to_list(length=10000)
        received_link_ids = [d["link_id"] for d in received_docs]

        query = {
            "user_id": {"$ne": user_id},
            "received_count": {"$lt": 50}
        }
        if received_link_ids:
            query["_id"] = {"$nin": received_link_ids}

        cursor = mongo_db.links.find(query).sort([("received_count", 1), ("_id", 1)]).limit(limit)
        results = []
        async for doc in cursor:
            doc["id"] = doc["_id"] # normalize id field
            results.append(doc)
        return results
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT id, swiggy_name, swiggy_link, received_count
                FROM links
                WHERE user_id != ?
                  AND received_count < 50
                  AND id NOT IN (SELECT link_id FROM link_distributions WHERE user_id = ?)
                ORDER BY received_count ASC, id ASC
                LIMIT ?
            """, (user_id, user_id, limit)) as cursor:
                return await cursor.fetchall()

async def record_link_distributions(user_id: int, link_ids: list):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if USE_MONGO:
        for lid in link_ids:
            try:
                await mongo_db.link_distributions.insert_one({
                    "user_id": user_id,
                    "link_id": lid,
                    "distributed_at": now
                })
            except Exception:
                pass # duplicate prevention
            await mongo_db.links.update_one({"_id": lid}, {"$inc": {"received_count": 1}})
        
        await mongo_db.users.update_one({"user_id": user_id}, {"$set": {"last_links_request_at": now}})
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            for lid in link_ids:
                await db.execute("""
                    INSERT OR IGNORE INTO link_distributions (user_id, link_id, distributed_at)
                    VALUES (?, ?, ?)
                """, (user_id, lid, now))
                await db.execute("""
                    UPDATE links SET received_count = received_count + 1 WHERE id = ?
                """, (lid,))
            
            await db.execute("""
                UPDATE users SET last_links_request_at = ? WHERE user_id = ?
            """, (now, user_id))
            await db.commit()

async def get_all_users():
    if USE_MONGO:
        return await mongo_db.users.find().sort("created_at", -1).to_list(length=10000)
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cursor:
                return await cursor.fetchall()

async def get_all_links_paginated(page: int = 1, per_page: int = 50):
    offset = (page - 1) * per_page
    if USE_MONGO:
        total_count = await mongo_db.links.count_documents({})
        cursor = mongo_db.links.find().sort("_id", 1).skip(offset).limit(per_page)
        rows = []
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            rows.append(doc)
        return rows, total_count
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT COUNT(*) as count FROM links") as cursor:
                total_count = (await cursor.fetchone())["count"]

            async with db.execute("""
                SELECT l.id, l.user_id, l.swiggy_name, l.swiggy_link, l.received_count, l.created_at, u.username
                FROM links l
                LEFT JOIN users u ON l.user_id = u.user_id
                ORDER BY l.id ASC
                LIMIT ? OFFSET ?
            """, (per_page, offset)) as cursor:
                rows = await cursor.fetchall()

        return rows, total_count

async def get_stats():
    if USE_MONGO:
        total_users = await mongo_db.users.count_documents({})
        total_links = await mongo_db.links.count_documents({})
        active_links = await mongo_db.links.count_documents({"received_count": {"$lt": 50}})
        total_distributions = await mongo_db.link_distributions.count_documents({})
    else:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT COUNT(*) as c FROM users") as cursor:
                total_users = (await cursor.fetchone())["c"]
            async with db.execute("SELECT COUNT(*) as c FROM links") as cursor:
                total_links = (await cursor.fetchone())["c"]
            async with db.execute("SELECT COUNT(*) as c FROM links WHERE received_count < 50") as cursor:
                active_links = (await cursor.fetchone())["c"]
            async with db.execute("SELECT COUNT(*) as c FROM link_distributions") as cursor:
                total_distributions = (await cursor.fetchone())["c"]

    return {
        "total_users": total_users,
        "total_links": total_links,
        "active_links": active_links,
        "total_distributions": total_distributions
    }

import asyncio
import database

# Sample links to seed into database
SAMPLE_LINKS = [
    {"name": "Akshaya", "link": "https://r.swiggy.com/buzzstreaks/ougwl_MTYzOTg4ODY5I0Frc2hheWE="},
    {"name": "Nitin", "link": "https://r.swiggy.com/buzzstreaks/ougwl_MTM4NTI1NzQ5I05pdGlu"}
]

async def seed():
    await database.init_db()
    added = 0
    skipped = 0

    for item in SAMPLE_LINKS:
        swiggy_link = item["link"].strip()
        swiggy_name = item["name"].strip()
        
        if await database.link_exists(swiggy_link):
            print(f"Skipped (already exists): {swiggy_link}")
            skipped += 1
            continue

        # Register system link under user_id 0
        await database.register_user_and_link(
            user_id=0,
            username="system_seed",
            first_name="System",
            swiggy_name=swiggy_name,
            swiggy_link=swiggy_link
        )
        print(f"Added link: {swiggy_name} - {swiggy_link}")
        added += 1

    print(f"\nSeeding complete! Added: {added}, Skipped: {skipped}")

if __name__ == "__main__":
    asyncio.run(seed())

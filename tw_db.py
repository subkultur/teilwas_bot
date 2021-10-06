import aiosqlite
from datetime import datetime

DB = 'db.sqlite'

async def search_db(user_id, type, kind, location, distance):
    curdate = str(datetime.now().strftime('%Y%m%d'))
    query = f"SELECT * FROM geteilt where expires_at > {curdate}"
    query += f" AND user_id <> {user_id}"
    if type != 'all':
        query += f" AND type = '{type}'"
    if kind != 'all':
        query += f" AND kind = '{kind}'"

    if location is not None:
        dist = int(distance) * 1000
        query += f" AND (PtDistWithin(geteilt.latlng, PointFromText('POINT({location.longitude} {location.latitude})', 4326), {dist})=TRUE)"
        
    query += ";"
    res = []
    async with aiosqlite.connect(DB) as db:
        await db.enable_load_extension(True)
        await db.load_extension('mod_spatialite')
        async with db.execute(query) as cursor:
            async for row in cursor:
                res.append(row)
    return res

async def delete_from_db(entry_uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute(f"DELETE FROM geteilt WHERE id = {entry_uid};")
        await db.commit()

async def search_own_db(user_id):
    query = f"SELECT * FROM geteilt WHERE user_id = {user_id};"
    res = []
    async with aiosqlite.connect(DB) as db:
        async with db.execute(query) as cursor:
            async for row in cursor:
                res.append(row)
    return res

async def add_db_entry(user_id, user_lang, type, kind, location, description, expires_at):
    currentDateTime = datetime.now().strftime('%Y%m%d')
    async with aiosqlite.connect(DB) as db:
        await db.enable_load_extension(True)
        await db.execute("SELECT load_extension('mod_spatialite');")
        last_row = None
        async with db.execute("INSERT INTO geteilt(user_id, user_lang, type, kind, lat, lng, desc, inserted_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", 
                (user_id, user_lang, type, kind, location.latitude, location.longitude, 
                description, currentDateTime, str(expires_at.strftime('%Y%m%d')))) as cursor:
            last_row = cursor.lastrowid
        await db.execute(f"UPDATE geteilt SET latlng = PointFromText('POINT({location.longitude} {location.latitude})', 4326) WHERE id = {last_row};")
        await db.commit()

async def check_point_col_exists(db):
    point_col_exists = False
    async with db.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'geteilt';") as cursor:
        async for row in cursor:
            point_col_exists = 'POINT' in row[0]
    return point_col_exists

async def init_db():
    async with aiosqlite.connect(DB) as db:
        point_col_exists = await check_point_col_exists(db)
        if not point_col_exists:
            await db.enable_load_extension(True)
            await db.execute("SELECT load_extension('mod_spatialite');")
            await db.execute("SELECT InitSpatialMetaData();")
            await db.execute("""CREATE TABLE IF NOT EXISTS geteilt (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_lang VARCHAR(2),
                type VARCHAR(10),
                kind VARCHAR(10),
                lat FLOAT,
                lng FLOAT,
                desc TEXT,
                inserted_at TEXT,
                expires_at TEXT
                );""")
            await db.execute("SELECT AddGeometryColumn('geteilt', 'latlng', 4326, 'POINT', 'XY');")
            await db.execute("SELECT CreateSpatialIndex('geteilt', 'latlng');")
            await db.commit()
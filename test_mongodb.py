import os

import pymongo
from dotenv import load_dotenv


load_dotenv()


def test_mongodb_connection():
    mongo_db_url = os.getenv("MONGO_DB_URL")
    if not mongo_db_url:
        raise RuntimeError("MONGO_DB_URL is not configured")

    client = pymongo.MongoClient(mongo_db_url, serverSelectionTimeoutMS=5_000)
    assert client.admin.command("ping")["ok"] == 1

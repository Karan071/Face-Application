from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
import time
from app.core.config import settings

def connect_to_milvus():
    """Connect to Milvus."""
    attempts = 5
    for attempt in range(attempts):
        try:
            if connections.has_connection("default"):
                connections.remove_connection("default")
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
                timeout=60
            )
            print(f"Connected to Milvus at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
            return
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    raise RuntimeError("Failed to connect to Milvus after several attempts")

def create_milvus_collection(collection_name):
    """Create or load a Milvus collection."""
    if not utility.has_collection(collection_name):
        schema = CollectionSchema(
            fields=[
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=255),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=4096),
            ],
            description=f"{collection_name} for storing embeddings"
        )
        collection = Collection(name=collection_name, schema=schema)
        print(f"Created collection: {collection_name}")
        collection.create_index(field_name="embedding", index_params={"metric_type": "IP", "index_type": "IVF_FLAT", "params": {"nlist": 128}})
        collection.flush()
        collection.load()
    else:
        collection = Collection(collection_name)
        collection.load()
    return collection

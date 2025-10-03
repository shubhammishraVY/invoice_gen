from db_configs.firebase_db import firestore_client

def list_collections():
    collections = firestore_client.collections()
    for col in collections:
        print("Collection ID:", col.id)

def list_documents(collection_name: str):
    docs = firestore_client.collection(collection_name).stream()
    for doc in docs:
        print(f"{doc.id} => {doc.to_dict()}")


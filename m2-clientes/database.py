from pymongo import MongoClient

# Por ahora usamos localhost. Más adelante, cumpliendo el RNF-06, lo pasaremos a un archivo .env
MONGO_URL = "mongodb://localhost:27017"

cliente_mongo = MongoClient(MONGO_URL)
db = cliente_mongo["m2_clientes_db"]
coleccion_clientes = db["clientes"]
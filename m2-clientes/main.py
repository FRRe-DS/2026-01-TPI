from fastapi import FastAPI, status, HTTPException
from bson import ObjectId
from models import Cliente
from database import coleccion_clientes

app = FastAPI(title="Módulo 2 - Clientes", version="1.0.0")

@app.post("/api/v1/clientes", status_code=status.HTTP_201_CREATED, tags=["Clientes"])
def crear_cliente(nuevo_cliente: Cliente):
    # Convertimos el modelo de Pydantic a un diccionario de Python (formato JSON)
    cliente_dict = nuevo_cliente.model_dump()
    
    # Lo insertamos en MongoDB
    resultado = coleccion_clientes.insert_one(cliente_dict)
    
    return {
        "mensaje": "Cliente creado exitosamente",
        "id_mongo": str(resultado.inserted_id)
    }

@app.get("/api/v1/clientes/{id_mongo}", tags=["Clientes"])
def obtener_cliente(id_mongo: str):
    # 1. Verificamos que el texto ingresado tenga el formato válido de 24 caracteres de MongoDB
    if not ObjectId.is_valid(id_mongo):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    
    # 2. Buscamos el documento en la base de datos
    cliente = coleccion_clientes.find_one({"_id": ObjectId(id_mongo)})
    
    # 3. Si MongoDB no encuentra nada, cortamos la ejecución y devolvemos un error 404
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    # 4. MongoDB devuelve el campo _id como un objeto binario. Lo convertimos a texto normal para poder mostrarlo.
    cliente["_id"] = str(cliente["_id"])
    
    return cliente

@app.get("/api/v1/clientes", tags=["Clientes"])
def listar_clientes():
    # Extraemos todos los documentos de la colección
    clientes = list(coleccion_clientes.find())
    
    # Convertimos el ObjectId binario a texto para cada cliente
    for cliente in clientes:
        cliente["_id"] = str(cliente["_id"])
        
    return clientes
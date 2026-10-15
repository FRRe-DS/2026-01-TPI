from fastapi import FastAPI, status, HTTPException, Depends
from security import validar_token
from bson import ObjectId
from models import Cliente
from database import coleccion_clientes

app = FastAPI(title="Módulo 2 - Clientes", version="1.0.0")

@app.post("/api/v1/clientes", tags=["Clientes"])
def crear_cliente(cliente: Cliente, usuario_actual: dict = Depends(validar_token)):
    # 1. Convertimos el modelo de Pydantic a diccionario
    cliente_dict = cliente.model_dump()
    
    # 2. Extraemos el ID único del usuario desde Keycloak
    # (El payload del token guarda este ID bajo la clave estándar "sub")
    keycloak_id = usuario_actual.get("sub")
    
    # 3. Añadimos el ID de Keycloak a los datos que vamos a guardar en MongoDB
    cliente_dict["usuario_id"] = keycloak_id
    
    # 4. Guardamos en la base de datos
    resultado = coleccion_clientes.insert_one(cliente_dict)
    
    return {
        "mensaje": "Cliente creado exitosamente",
        "id_mongo": str(resultado.inserted_id),
        "usuario_keycloak": keycloak_id
    }

@app.get("/api/v1/clientes/{id_mongo}", tags=["Clientes"])
def obtener_cliente(id_mongo: str, usuario_actual: dict = Depends(validar_token)):
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
def listar_clientes(usuario_actual: dict = Depends(validar_token)):
    # Si la ejecución llega a esta línea, es porque el token es válido
    # Extraemos todos los documentos de la colección
    clientes = list(coleccion_clientes.find())
    
    # Convertimos el ObjectId binario a texto para cada cliente
    for cliente in clientes:
        cliente["_id"] = str(cliente["_id"])
        
    return clientes


@app.put("/api/v1/clientes/{id_mongo}", tags=["Clientes"])
def actualizar_cliente(id_mongo: str, cliente_actualizado: Cliente, usuario_actual: dict = Depends(validar_token)):
    # 1. Verificamos que el ID sea válido
    if not ObjectId.is_valid(id_mongo):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    
    # 2. Convertimos el modelo validado de Pydantic a un diccionario
    datos_actualizar = cliente_actualizado.model_dump()
    
    # 3. Le decimos a MongoDB que busque por ID y aplique los nuevos datos con $set
    resultado = coleccion_clientes.update_one(
        {"_id": ObjectId(id_mongo)},
        {"$set": datos_actualizar}
    )
    
    # 4. Si matched_count es 0, significa que el ID no existe en la base de datos
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    return {
        "mensaje": "Cliente actualizado exitosamente",
        "modificado": resultado.modified_count > 0 # Devuelve true si realmente se cambió algún dato
    }

@app.delete("/api/v1/clientes/{id_mongo}", tags=["Clientes"])
def eliminar_cliente(id_mongo: str, usuario_actual: dict = Depends(validar_token)):
    # 1. Verificamos que el ID sea válido
    if not ObjectId.is_valid(id_mongo):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    
    # 2. Le ordenamos a MongoDB que busque y elimine el documento
    resultado = coleccion_clientes.delete_one({"_id": ObjectId(id_mongo)})
    
    # 3. Si deleted_count es 0, significa que no encontró a nadie con ese ID
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    return {"mensaje": "Cliente eliminado exitosamente"}
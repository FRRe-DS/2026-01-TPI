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
        
    # --- NUEVA REGLA DE PROPIEDAD (Autorización) ---
    # 4. Verificamos que el dueño del documento sea el mismo que está haciendo la petición
    if cliente.get("usuario_id") != usuario_actual.get("sub"):
        raise HTTPException(status_code=403, detail="No tienes permiso para acceder a este cliente")
        
    # 5. MongoDB devuelve el campo _id como un objeto binario. Lo convertimos a texto normal.
    cliente["_id"] = str(cliente["_id"])
    
    return cliente

@app.get("/api/v1/clientes", tags=["Clientes"])
def listar_clientes(usuario_actual: dict = Depends(validar_token)):
    # 1. Extraemos tu ID de Keycloak
    mi_id = usuario_actual.get("sub")
    
    # 2. Le pedimos a Mongo que traiga ÚNICAMENTE los documentos que tengan tu ID
    cursor = coleccion_clientes.find({"usuario_id": mi_id})
    
    # 3. Procesamos la lista para convertir los ObjectIds a texto
    lista_clientes = []
    for cliente in cursor:
        cliente["_id"] = str(cliente["_id"])
        lista_clientes.append(cliente)
        
    return lista_clientes


@app.put("/api/v1/clientes/{id_mongo}", tags=["Clientes"])
def actualizar_cliente(id_mongo: str, cliente_actualizado: Cliente, usuario_actual: dict = Depends(validar_token)):
    # 1. Verificamos que el ID sea válido
    if not ObjectId.is_valid(id_mongo):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    
    # 2. BUSCAMOS el cliente actual en la base de datos PRIMERO
    cliente = coleccion_clientes.find_one({"_id": ObjectId(id_mongo)})
    
    # 3. Si no existe, error 404
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # 4. AHORA SÍ comparamos los permisos
    if cliente.get("usuario_id") != usuario_actual.get("sub"):
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar a este cliente")
    
    # 5. Todo es válido y seguro. Convertimos y actualizamos.
    datos_actualizar = cliente_actualizado.model_dump()
    resultado = coleccion_clientes.update_one(
        {"_id": ObjectId(id_mongo)},
        {"$set": datos_actualizar}
    )
    
    return {
        "mensaje": "Cliente actualizado exitosamente",
        "modificado": resultado.modified_count > 0 # Devuelve true si realmente se cambió algún dato
    }

@app.delete("/api/v1/clientes/{id_mongo}", tags=["Clientes"])
def eliminar_cliente(id_mongo: str, usuario_actual: dict = Depends(validar_token)):
    # 1. Verificamos que el ID sea válido
    if not ObjectId.is_valid(id_mongo):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    
    # 2. BUSCAMOS el cliente actual en la base de datos PRIMERO
    cliente = coleccion_clientes.find_one({"_id": ObjectId(id_mongo)})
    
    # 3. Si no existe, error 404
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # 4. AHORA SÍ comparamos los permisos
    if cliente.get("usuario_id") != usuario_actual.get("sub"):
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar a este cliente")
    
    # 5. Todo es válido y seguro. Eliminamos de Mongo.
    coleccion_clientes.delete_one({"_id": ObjectId(id_mongo)})
    
    return {"mensaje": "Cliente eliminado exitosamente"}
from mysql.connector import Error

import conexion


db = conexion.Conexion()


class crud_usss013325:
    def _consultar(self, sql, datos=None):
        filas = db.consultar(sql, datos)
        if filas is None:
            raise RuntimeError("No se pudo consultar la tabla de usuarios.")
        return filas

    def consultar(self, buscar=""):
        termino = f"%{str(buscar).strip()}%"
        return self._consultar(
            """
            SELECT idUsuario, usuario, clave, nombre, direccion, telefono
            FROM usuarios_usss013325
            WHERE usuario LIKE %s OR nombre LIKE %s OR direccion LIKE %s
                OR telefono LIKE %s
            ORDER BY idUsuario
            """,
            (termino, termino, termino, termino),
        )

    def autenticar(self, usuario, clave):
        filas = self._consultar(
            """
            SELECT idUsuario, usuario, nombre
            FROM usuarios_usss013325
            WHERE usuario=%s AND clave=%s
            """,
            (str(usuario).strip(), str(clave)),
        )
        return filas[0] if filas else None

    def administrar(self, datos):
        try:
            accion = datos.get("accion")
            usuario = str(datos.get("usuario", "")).strip()
            nombre = str(datos.get("nombre", "")).strip()
            direccion = str(datos.get("direccion", "")).strip()
            telefono = str(datos.get("telefono", "")).strip()
            clave = str(datos.get("clave", ""))

            if accion in ("nuevo", "modificar"):
                if not usuario or not nombre or not direccion or not telefono:
                    return {"ok": False, "msg": "Complete todos los campos requeridos."}
                if len(usuario) > 35 or len(nombre) > 85 or len(direccion) > 100 or len(telefono) > 9:
                    return {"ok": False, "msg": "Uno o más campos exceden el tamaño permitido."}

            if accion == "nuevo":
                if not clave or len(clave) > 35:
                    return {"ok": False, "msg": "La clave es obligatoria y debe tener hasta 35 caracteres."}
                sql = """
                    INSERT INTO usuarios_usss013325
                        (usuario, clave, nombre, direccion, telefono)
                    VALUES (%s, %s, %s, %s, %s)
                """
                valores = (usuario, clave, nombre, direccion, telefono)
            elif accion == "modificar":
                id_usuario = int(datos["idUsuario"])
                if clave:
                    if len(clave) > 35:
                        return {"ok": False, "msg": "La clave debe tener hasta 35 caracteres."}
                    sql = """
                        UPDATE usuarios_usss013325
                        SET usuario=%s, clave=%s, nombre=%s, direccion=%s, telefono=%s
                        WHERE idUsuario=%s
                    """
                    valores = (usuario, clave, nombre, direccion, telefono, id_usuario)
                else:
                    sql = """
                        UPDATE usuarios_usss013325
                        SET usuario=%s, nombre=%s, direccion=%s, telefono=%s
                        WHERE idUsuario=%s
                    """
                    valores = (usuario, nombre, direccion, telefono, id_usuario)
            elif accion == "eliminar":
                id_usuario = int(datos["idUsuario"])
                sql = "DELETE FROM usuarios_usss013325 WHERE idUsuario=%s"
                valores = (id_usuario,)
            else:
                return {"ok": False, "msg": "Acción no válida."}

            resultado = db.ejecutar(sql, valores)
            return {"ok": resultado == "ok", "msg": resultado}
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "msg": "Los datos del usuario no son válidos."}
        except Error as error:
            return {"ok": False, "msg": f"Error al guardar el usuario: {error}"}

from mysql.connector.errors import Error
import conexion

db = conexion.Conexion()

class crud_productos:
    def consultar(self, buscar):
        return db.consultar(f"SELECT * FROM productos WHERE descripcion LIKE '%{buscar}%'")

    def administrar(self, datos):
        try:
            if datos['accion']=='nuevo':
                sql = """
                    INSERT INTO productos(codigo,descripcion,estado)
                    VALUES(%s,%s,%s)
                """
                valores = (datos['codigo'],datos['descripcion'],datos['estado'])
            elif datos['accion']=='modificar':
                sql = """
                    UPDATE productos SET codigo=%s,descripcion=%s,estado=%s
                    WHERE idProducto=%s
                """
                valores = (datos['codigo'],datos['descripcion'],datos['estado'],datos['idProducto'])
            else:
                sql = """
                    DELETE FROM productos WHERE idProducto=%s
                """
                valores = (datos['idProducto'],)
            return db.ejecutar(sql,valores)
        except Error as e:
            return f"Error al guardar el producto: {e}"
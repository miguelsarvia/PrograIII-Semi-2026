from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import crud_clientes
import crud_periodos
import crud_productos
import crud_usss013325
import json
 
port = 3000
crudClientes = crud_clientes.crud_clientes()
crudProductos = crud_productos.crud_productos()
crudUsuarios = crud_usss013325.crud_usss013325()

class miServidor(SimpleHTTPRequestHandler):
    def _responder_json(self, datos, estado=200):
        contenido = json.dumps(datos).encode("utf-8")
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)

    def _leer_json(self):
        longitud = int(self.headers.get("Content-Length", "0"))
        datos = self.rfile.read(longitud)
        try:
            return json.loads(datos.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def do_POST(self):
        ruta = urlparse(self.path).path
        datos = self._leer_json()
        if datos is None or not isinstance(datos, dict):
            self._responder_json({"ok": False, "msg": "El cuerpo debe ser JSON válido."}, 400)
            return

        if ruta == "/periodos":
            respuesta = crud_periodos.administrar(datos)
        elif ruta == "/producto" or datos.get("modulo") == "producto":
            respuesta = {'msg': crudProductos.administrar(datos)}
        elif ruta == "/usuarios":
            respuesta = crudUsuarios.administrar(datos)
        else:
            respuesta = {'msg': crudClientes.administrar(datos)}
        self._responder_json(respuesta)
 
    def do_GET(self):
        urlParse = urlparse(self.path)
        qs = parse_qs(urlParse.query)

        if urlParse.path == "/":
            self.path = "/modulos/usuarios.html"
            return SimpleHTTPRequestHandler.do_GET(self)

        if urlParse.path == "/clientes":
            buscar = qs.get('buscar', [''])[0]
            datos = crudClientes.consultar(buscar)
            self._responder_json(datos)
 
        elif urlParse.path == "/periodos":
            datos = crud_periodos.listar(qs.get('idCliente', ['0'])[0])
            self._responder_json(datos)

        elif urlParse.path == "/productos":
            buscar = qs.get('buscar', [''])[0]
            datos = crudProductos.consultar(buscar)
            self._responder_json(datos)
        elif urlParse.path == "/usuarios":
            buscar = qs.get("buscar", [""])[0]
            try:
                self._responder_json(crudUsuarios.consultar(buscar))
            except RuntimeError as error:
                self._responder_json({"ok": False, "msg": str(error)}, 500)
        else:
            return SimpleHTTPRequestHandler.do_GET(self)
 
if __name__ == "__main__":
    print(f"Servidor corriendo en el puerto {port}")
    server = HTTPServer(("localhost", port), miServidor)
    server.serve_forever()
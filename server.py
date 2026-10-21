from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import crud_usss013325
import json
 
port = 3000
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

        if ruta == "/login":
            try:
                usuario = crudUsuarios.autenticar(
                    datos.get("usuario", ""),
                    datos.get("clave", ""),
                )
            except RuntimeError as error:
                self._responder_json({"ok": False, "msg": str(error)}, 500)
                return
            if not usuario:
                self._responder_json(
                    {"ok": False, "msg": "Usuario o clave incorrectos."},
                    401,
                )
                return
            self._responder_json({
                "ok": True,
                "msg": "Inicio de sesión con éxito.",
                "usuario": usuario["usuario"],
                "nombre": usuario["nombre"],
            })
            return

        if ruta != "/usuarios":
            self._responder_json({"ok": False, "msg": "Ruta no encontrada."}, 404)
            return

        respuesta = crudUsuarios.administrar(datos)
        self._responder_json(respuesta)
 
    def do_GET(self):
        urlParse = urlparse(self.path)
        qs = parse_qs(urlParse.query)

        if urlParse.path == "/":
            self.path = "/modulos/usuarios.html"
            return SimpleHTTPRequestHandler.do_GET(self)

        if urlParse.path == "/usuarios":
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
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
 
import crud_clientes
import impuesto as imp
 
# Misma conexión que usa crud_clientes: así siempre ve los clientes recién guardados
db = crud_clientes.db
 
PRODUCTO = "11801"                      # un solo producto por ahora
TARIFAS = imp.tarifas_de_ejemplo(PRODUCTO)
TIPO_EMPRESA = "empresa"                # valor del campo "tipo" que paga el impuesto
 
 
# ---------------------------------------------------------------- utilidades
def _fecha(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])
 
 
def _periodo(f) -> imp.Periodo:
    return imp.Periodo(
        cliente_id=int(f["idCliente"]),
        producto=f["producto"],
        desde=_fecha(f["desde"]),
        hasta=_fecha(f["hasta"]),
        balance=Decimal(str(f["balance"])),
        precio=Decimal(str(f["precio"])),
        cantidad=Decimal(str(f["cantidad"])),
        formula_version=f["formula_version"],
        facturado=bool(f["facturado"]),
    )
 
 
def _a_json(f) -> dict:
    p = _periodo(f)
    return {
        "idPeriodo": f["idPeriodo"],
        "desde": p.desde.isoformat(),
        "hasta": p.hasta.isoformat(),           # exclusivo: no se cobra ese día
        "balance": str(p.balance),
        "impuestoMensual": str(p.precio_mostrado),
        "facturado": p.facturado,
    }
 
 
def _filas(id_cliente: int):
    # id_cliente ya es int (validado), por eso no hay inyección SQL aquí
    return db.consultar(
        f"SELECT * FROM periodos_actividad WHERE idCliente={int(id_cliente)} ORDER BY desde"
    )
 
 
# ------------------------------------------------------------------ consultas
def listar(id_cliente):
    try:
        return [_a_json(f) for f in _filas(int(id_cliente))]
    except (ValueError, TypeError):
        return []
 
 
# ---------------------------------------------------------------- operaciones
def administrar(datos: dict) -> dict:
    accion = datos.get("accion")
    if accion == "nuevo":
        return _registrar(datos)
    if accion == "eliminar":
        return _eliminar(datos)
    return {"ok": False, "msg": "Acción no válida."}
 
 
def _registrar(datos: dict) -> dict:
    try:
        id_cliente = int(datos["idCliente"])
        desde = date.fromisoformat(str(datos["fechaDesde"]))
        hasta = date.fromisoformat(str(datos["fechaHasta"]))
 
        cliente = db.consultar(
            f"SELECT tipo FROM clientes WHERE idCliente={id_cliente}"
        )
        if not cliente:
            return {"ok": False, "msg": "Cliente no encontrado."}
        es_empresa = str(cliente[0]["tipo"]).strip().lower() == TIPO_EMPRESA
 
        texto = str(datos.get("monto", "")).strip().replace(",", "")
        monto = Decimal(texto) if texto else Decimal("0")
 
        periodo, avisos = imp.crear_periodo(
            cliente_id=id_cliente,
            es_empresa=es_empresa,
            producto=PRODUCTO,
            desde=desde,
            hasta=hasta,
            balance=monto,
            tarifas=TARIFAS,
            formula=str(datos.get("formula", "bloques")),
            existentes=[_periodo(f) for f in _filas(id_cliente)],
        )
    except imp.ErrorImpuesto as e:
        return {"ok": False, "msg": str(e)}
    except (KeyError, ValueError, TypeError, InvalidOperation):
        return {"ok": False, "msg": "Complete monto, fecha desde y fecha hasta con valores válidos."}
 
    sql = """
        INSERT INTO periodos_actividad
            (idCliente, producto, desde, hasta, balance, precio, cantidad,
             formula_version, fecha_calculo, facturado)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0)
    """
    valores = (
        periodo.cliente_id, periodo.producto, periodo.desde, periodo.hasta,
        periodo.balance, periodo.precio, periodo.cantidad,
        periodo.formula_version, periodo.fecha_calculo,
    )
    resultado = db.ejecutar(sql, valores)
    return {
        "ok": True,
        "msg": resultado,
        "impuestoMensual": str(periodo.precio_mostrado),
        "avisos": avisos,
    }
 
 
def _eliminar(datos: dict) -> dict:
    try:
        id_periodo = int(datos["idPeriodo"])
    except (KeyError, ValueError, TypeError):
        return {"ok": False, "msg": "Período no válido."}
    fila = db.consultar(
        f"SELECT facturado FROM periodos_actividad WHERE idPeriodo={id_periodo}"
    )
    if not fila:
        return {"ok": False, "msg": "Período no encontrado."}
    if fila[0]["facturado"]:
        return {"ok": False, "msg": "El período ya fue utilizado en recibos y no puede eliminarse."}
    resultado = db.ejecutar("DELETE FROM periodos_actividad WHERE idPeriodo=%s", (id_periodo,))
    return {"ok": True, "msg": resultado}
 
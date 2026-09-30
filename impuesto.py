"""Tax on Economic Activities.
 
Lógica pura (sin framework ni base de datos) para poder integrarla en
cualquier proyecto: Flask, FastAPI, Django, SQLite, etc.
 
Reglas implementadas (numeración del documento de requerimiento):
  Historia de usuario: solo las empresas pagan; un cliente particular
             queda con impuesto 0 (se registra el período, precio 0)
  RF02-RF06  períodos [Desde, Hasta), sin superposición, aviso de huecos
  RF09/RF14  un período facturado no se recalcula
  RF10-RF13  selección de tarifa única, sin usar precio general
  Sec. 10    fórmula por bloques (CEIL) y tarifa porcentual
  Sec. 11    Decimal, 6 decimales internos, 2 al mostrar/cobrar
  Sec. 15    cargo = cantidad x precio mensual x meses aplicables
"""
from __future__ import annotations
 
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Iterable, Optional
 
D = Decimal
BLOQUE = D("1000")
DOS = D("0.01")
SEIS = D("0.000001")
FORMULA_VERSION = "bloques-ceil-v2"
FORMULA_PARTICULAR = "particular-sin-impuesto"
FORMULA_PROPORCIONAL = "proporcional-v1"   # fórmula anterior, solo para históricos
 
 
# --------------------------------------------------------------- errores
class ErrorImpuesto(Exception):
    """Base de los errores de negocio; el mensaje es apto para el usuario."""
 
 
class BalanceInvalido(ErrorImpuesto):
    pass
 
 
class FechasInvalidas(ErrorImpuesto):
    pass
 
 
class PeriodoSuperpuesto(ErrorImpuesto):
    pass
 
 
class TarifaInexistente(ErrorImpuesto):
    pass
 
 
class TarifasSuperpuestas(ErrorImpuesto):
    pass
 
 
class PeriodoFacturado(ErrorImpuesto):
    pass
 
 
# ---------------------------------------------------------------- modelos
@dataclass(frozen=True)
class Tarifa:
    producto: str              # p. ej. "11801" (comercio) o "11802" (industria)
    desde: Decimal
    hasta: Decimal
    precio_base: Decimal
    adicional: Decimal
    porcentaje: Decimal = D("0")
    vigente_desde: date = date.min
    vigente_hasta: Optional[date] = None   # exclusivo; None = sin fin
    version: str = "v1"
 
    def vigente_en(self, fecha: date) -> bool:
        return self.vigente_desde <= fecha and (
            self.vigente_hasta is None or fecha < self.vigente_hasta
        )
 
    def contiene(self, balance: Decimal) -> bool:
        return self.desde <= balance <= self.hasta        # RF10 inclusivo
 
 
@dataclass(frozen=True)
class Resultado:
    balance: Decimal
    tarifa: Tarifa
    excedente: Decimal
    bloques: int
    precio_interno: Decimal     # hasta 6 decimales
    precio_mensual: Decimal     # 2 decimales (lo que se muestra y cobra)
    formula_version: str
    fecha_calculo: datetime
 
    def detalle(self) -> str:                              # RF18
        t = self.tarifa
        return (
            f"Balance {self.balance} | rango {t.desde} a {t.hasta} | "
            f"base {t.precio_base} | excedente {self.excedente} | "
            f"bloques {self.bloques} | adicional {t.adicional} | "
            f"% {t.porcentaje} | mensual {self.precio_mensual}"
        )
 
 
@dataclass(frozen=True)
class Periodo:
    cliente_id: int
    producto: str
    desde: date
    hasta: date                 # exclusivo
    balance: Decimal
    precio: Decimal             # precio histórico, nunca se recalcula solo
    cantidad: Decimal = D("1.00")
    tarifa: Optional[Tarifa] = None
    formula_version: str = FORMULA_VERSION
    fecha_calculo: Optional[datetime] = None
    facturado: bool = False
 
    @property
    def precio_mostrado(self) -> Decimal:
        return redondear(self.precio)
 
    @property
    def subtotal(self) -> Decimal:
        return redondear(self.cantidad * self.precio)
 
 
# ---------------------------------------------------------------- cálculo
def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(DOS, rounding=ROUND_HALF_UP)
 
 
def seleccionar_tarifa(
    balance: Decimal, tarifas: Iterable[Tarifa], producto: str, fecha: date
) -> Tarifa:
    candidatas = [
        t for t in tarifas
        if t.producto == producto and t.vigente_en(fecha) and t.contiene(balance)
    ]
    if not candidatas:                                     # RF11 y RF13
        raise TarifaInexistente(
            "No existe una tarifa configurada para el balance indicado."
        )
    if len(candidatas) > 1:                                # RF12
        raise TarifasSuperpuestas(
            "Existe más de una tarifa aplicable. Corrija la tabla tarifaria."
        )
    return candidatas[0]
 
 
def calcular_impuesto(
    balance: Decimal, tarifa: Tarifa, ahora: Optional[datetime] = None
) -> Resultado:
    balance = D(balance)
    if balance <= 0:
        raise BalanceInvalido("Ingrese un balance mayor que cero.")
 
    if tarifa.porcentaje > 0:                              # 10.4
        excedente, bloques = D("0"), 0
        precio = balance * tarifa.porcentaje / D("100")
    else:                                                  # 10.1
        excedente = balance - tarifa.desde
        bloques = int(
            (excedente / BLOQUE).to_integral_value(rounding=ROUND_CEILING)
        )
        precio = tarifa.precio_base + bloques * tarifa.adicional
 
    precio = precio.quantize(SEIS, rounding=ROUND_HALF_UP)
    return Resultado(
        balance=balance,
        tarifa=tarifa,
        excedente=excedente,
        bloques=bloques,
        precio_interno=precio,
        precio_mensual=redondear(precio),
        formula_version=FORMULA_VERSION,
        fecha_calculo=ahora or datetime.now(),
    )
 
 
def calcular_impuesto_proporcional(
    balance: Decimal, tarifa: Tarifa, ahora: Optional[datetime] = None
) -> Resultado:
    """Fórmula anterior (sección 12 de la guía), solo para registrar períodos
    históricos: base + ((balance - límite inferior) / 1,000 x adicional).
    Con 700.00 da 1.50 + (200 / 1,000 x 3.00) = 2.10."""
    balance = D(balance)
    if balance <= 0:
        raise BalanceInvalido("Ingrese un balance mayor que cero.")
    if tarifa.porcentaje > 0:               # la tarifa porcentual no cambia
        return calcular_impuesto(balance, tarifa, ahora)
 
    excedente = balance - (tarifa.desde - DOS)      # 500.01 -> se mide desde 500.00
    precio = tarifa.precio_base + excedente / BLOQUE * tarifa.adicional
    precio = precio.quantize(SEIS, rounding=ROUND_HALF_UP)
    return Resultado(
        balance=balance, tarifa=tarifa, excedente=excedente, bloques=0,
        precio_interno=precio, precio_mensual=redondear(precio),
        formula_version=FORMULA_PROPORCIONAL,
        fecha_calculo=ahora or datetime.now(),
    )
 
 
# ---------------------------------------------------------------- períodos
def _se_superponen(d1: date, h1: date, d2: date, h2: date) -> bool:
    # [d1,h1) y [d2,h2): si solo se tocan en el borde NO hay superposición (RF05)
    return d1 < h2 and d2 < h1
 
 
def detectar_huecos(periodos: Iterable[Periodo]) -> list[tuple[date, date]]:
    """RF06: espacios sin cobertura entre períodos de un mismo cliente/producto."""
    ordenados = sorted(periodos, key=lambda p: p.desde)
    return [
        (a.hasta, b.desde)
        for a, b in zip(ordenados, ordenados[1:])
        if b.desde > a.hasta
    ]
 
 
def crear_periodo(
    *,
    cliente_id: int,
    es_empresa: bool,
    producto: str,
    desde: date,
    hasta: date,
    balance: Decimal,
    tarifas: Iterable[Tarifa],
    existentes: Iterable[Periodo] = (),
    cantidad: Decimal = D("1.00"),
    formula: str = "bloques",               # "proporcional" solo para históricos
    ahora: Optional[datetime] = None,
) -> tuple[Periodo, list[str]]:
    """Valida, calcula y devuelve (período, advertencias). No guarda nada:
    persistirlo (con su auditoría) en una transacción es tarea del llamador."""
    if formula not in ("bloques", "proporcional"):
        raise ErrorImpuesto("Fórmula no válida.")
    balance = D(balance)
    if es_empresa and balance <= 0:
        raise BalanceInvalido("Ingrese un balance mayor que cero.")
    if not desde < hasta:                                  # RF03
        raise FechasInvalidas("La fecha Hasta debe ser posterior a la fecha Desde.")
 
    existentes = [
        p for p in existentes
        if p.cliente_id == cliente_id and p.producto == producto
    ]
    for p in existentes:                                   # RF04
        if _se_superponen(desde, hasta, p.desde, p.hasta):
            raise PeriodoSuperpuesto(
                "El período indicado se superpone con un período existente."
            )
 
    if es_empresa:
        tarifa = seleccionar_tarifa(balance, tarifas, producto, desde)
        calcular = (
            calcular_impuesto_proporcional if formula == "proporcional"
            else calcular_impuesto
        )
        r = calcular(balance, tarifa, ahora)
        nuevo = Periodo(
            cliente_id=cliente_id, producto=producto, desde=desde, hasta=hasta,
            balance=balance, precio=r.precio_interno, cantidad=D(cantidad),
            tarifa=tarifa, formula_version=r.formula_version,
            fecha_calculo=r.fecha_calculo,
        )
    else:                                   # particular: no paga el impuesto
        nuevo = Periodo(
            cliente_id=cliente_id, producto=producto, desde=desde, hasta=hasta,
            balance=balance, precio=D("0"), cantidad=D(cantidad), tarifa=None,
            formula_version=FORMULA_PARTICULAR,
            fecha_calculo=ahora or datetime.now(),
        )
    avisos = [
        f"Hay un espacio sin cobertura entre {a} y {b}."
        for a, b in detectar_huecos([*existentes, nuevo])
        if desde in (a, b) or hasta in (a, b)
    ]
    return nuevo, avisos
 
 
def recalcular_periodo(
    periodo: Periodo, tarifas: Iterable[Tarifa], ahora: Optional[datetime] = None
) -> Periodo:
    """Solo para períodos NO facturados y con recálculo autorizado (RF09/RF14)."""
    if periodo.facturado:
        raise PeriodoFacturado(
            "El período ya fue utilizado en recibos y no puede recalcularse automáticamente."
        )
    if periodo.formula_version in (FORMULA_PARTICULAR, FORMULA_PROPORCIONAL):
        return periodo                      # particular en 0 / histórico intacto
    tarifa = seleccionar_tarifa(periodo.balance, tarifas, periodo.producto, periodo.desde)
    r = calcular_impuesto(periodo.balance, tarifa, ahora)
    return replace(
        periodo, precio=r.precio_interno, tarifa=tarifa,
        formula_version=r.formula_version, fecha_calculo=r.fecha_calculo,
    )
 
 
# ------------------------------------------------------------------ cobro
def _indice_mes(d: date) -> int:
    return d.year * 12 + d.month - 1
 
 
def meses_aplicables(periodo: Periodo, rec_desde: date, rec_hasta: date) -> int:
    """Meses del recibo [rec_desde, rec_hasta) que caen dentro del período.
    Supone límites en día 1 de mes, como los del documento."""
    ini, fin = max(periodo.desde, rec_desde), min(periodo.hasta, rec_hasta)
    return 0 if ini >= fin else _indice_mes(fin) - _indice_mes(ini)
 
 
def cargo_recibo(
    periodos: Iterable[Periodo], rec_desde: date, rec_hasta: date
) -> Decimal:
    """Suma por período: cantidad x precio mensual x meses aplicables.
    Nunca usa la suma histórica de precios (los 20.10 del ejemplo)."""
    total = sum(
        (p.cantidad * p.precio * meses_aplicables(p, rec_desde, rec_hasta)
         for p in periodos),
        D("0"),
    )
    return redondear(total)
 
 
# ------------------------------------------------------- tabla de ejemplo
# Rangos de las capturas. OJO: falta 6,000.01 a 8,000.00 (pendiente 18.2);
# el sistema debe rechazar esos balances hasta que se configure (CA 10).
_FILAS = [
    ("0.01", "500.00", "1.50", "0.00", "0"),
    ("500.01", "1000.00", "1.50", "3.00", "0"),
    ("1000.01", "2000.00", "3.00", "3.00", "0"),
    ("2000.01", "3000.00", "6.00", "3.00", "0"),
    ("3000.01", "6000.00", "9.00", "2.00", "0"),
    ("8000.01", "18000.00", "15.00", "2.00", "0"),
    ("18000.01", "30000.00", "39.00", "2.00", "0"),
    ("30000.01", "60000.00", "63.00", "1.00", "0"),
    ("60000.01", "100000.00", "93.00", "0.80", "0"),
    ("100000.01", "200000.00", "125.00", "0.70", "0"),
    ("200000.01", "300000.00", "195.00", "0.60", "0"),
    ("300000.01", "400000.00", "255.00", "0.45", "0"),
    ("400000.01", "500000.00", "300.00", "0.40", "0"),
    ("500000.01", "1000000.00", "340.00", "0.30", "0"),
    ("1000000.01", "99999999.99", "490.00", "0.18", "0"),
]
 
 
def tarifas_de_ejemplo(producto: str, vigente_desde: date = date(2000, 1, 1)) -> list[Tarifa]:
    """Cada producto tiene su propia tabla (CA 11): no se comparten por defecto."""
    return [
        Tarifa(producto, D(a), D(b), D(c), D(d), D(e), vigente_desde)
        for a, b, c, d, e in _FILAS
    ]
 
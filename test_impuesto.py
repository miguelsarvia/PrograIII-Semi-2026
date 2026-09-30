from dataclasses import replace
from datetime import date
from decimal import Decimal as D
 
import pytest
 
from impuesto import (
    Periodo, PeriodoFacturado, PeriodoSuperpuesto, TarifaInexistente,
    TarifasSuperpuestas, Tarifa, BalanceInvalido,
    FechasInvalidas, calcular_impuesto, cargo_recibo, crear_periodo,
    detectar_huecos, recalcular_periodo, seleccionar_tarifa, tarifas_de_ejemplo,
)
 
P = "11801"
TARIFAS = tarifas_de_ejemplo(P)
 
 
def precio(balance):
    t = seleccionar_tarifa(D(balance), TARIFAS, P, date(2026, 1, 1))
    return calcular_impuesto(D(balance), t).precio_mensual
 
 
def test_ca01_ca02_bloque_completo():
    assert precio("545.00") == D("4.50")
    assert precio("550.00") == D("4.50")
 
 
def test_ca03_limite_inclusivo_primer_rango():
    t = seleccionar_tarifa(D("500.00"), TARIFAS, P, date(2026, 1, 1))
    assert t.desde == D("0.01")
    assert calcular_impuesto(D("500.00"), t).precio_mensual == D("1.50")
 
 
def test_ca04_inicio_de_rango_sin_bloque_adicional():
    t = seleccionar_tarifa(D("500.01"), TARIFAS, P, date(2026, 1, 1))
    r = calcular_impuesto(D("500.01"), t)
    assert t.desde == D("500.01") and r.bloques == 0
    assert r.precio_mensual == D("1.50")
 
 
def test_ca10_rango_faltante_se_rechaza():
    with pytest.raises(TarifaInexistente):
        precio("7000.00")
 
 
def test_ca13_porcentaje_decimal_no_se_trunca():
    t = Tarifa(P, D("0.01"), D("99999.99"), D("0"), D("0"), D("1.50"))
    assert calcular_impuesto(D("50000.00"), t).precio_mensual == D("750.00")
 
 
def test_tarifas_superpuestas_bloquean():
    duplicada = TARIFAS + [TARIFAS[1]]
    with pytest.raises(TarifasSuperpuestas):
        seleccionar_tarifa(D("550"), duplicada, P, date(2026, 1, 1))
 
 
def test_ca11_productos_no_se_intercambian():
    with pytest.raises(TarifaInexistente):
        seleccionar_tarifa(D("550"), tarifas_de_ejemplo("11802"), P, date(2026, 1, 1))
 
 
def _crear(desde, hasta, balance="550.00", existentes=()):
    return crear_periodo(
        cliente_id=1, es_empresa=True, producto=P, desde=desde, hasta=hasta,
        balance=D(balance), tarifas=TARIFAS, existentes=existentes,
    )
 
 
def test_ca14_periodos_superpuestos():
    p1, _ = _crear(date(2025, 1, 1), date(2026, 1, 1))
    with pytest.raises(PeriodoSuperpuesto):
        _crear(date(2025, 6, 1), date(2026, 6, 1), existentes=[p1])
 
 
def test_rf05_periodos_contiguos_permitidos_y_ca07_mismo_balance():
    p1, _ = _crear(date(2025, 1, 1), date(2026, 1, 1))
    p2, avisos = _crear(date(2026, 1, 1), date(2027, 1, 1), existentes=[p1])
    assert p2.precio_mostrado == p1.precio_mostrado == D("4.50")
    assert avisos == []
 
 
def test_rf06_aviso_de_hueco():
    p1, _ = _crear(date(2022, 1, 1), date(2023, 1, 1))
    _, avisos = _crear(date(2024, 1, 1), date(2025, 1, 1), existentes=[p1])
    assert len(avisos) == 1
 
 
def test_validaciones_de_entrada():
    with pytest.raises(BalanceInvalido):
        _crear(date(2026, 1, 1), date(2027, 1, 1), balance="0")
    with pytest.raises(FechasInvalidas):
        _crear(date(2027, 1, 1), date(2026, 1, 1))
 
 
def test_ca08_historico_2022_se_conserva():
    historico = Periodo(1, P, date(2022, 1, 1), date(2023, 1, 1),
                        D("700.00"), D("2.10"), facturado=True)
    assert historico.precio_mostrado == D("2.10")
    with pytest.raises(PeriodoFacturado):        # RF09 / RF14
        recalcular_periodo(historico, TARIFAS)
    # Si no estuviera facturado y se autorizara, la fórmula nueva daría 4.50
    assert recalcular_periodo(replace(historico, facturado=False), TARIFAS).precio_mostrado == D("4.50")
 
 
def test_ca12_cobro_usa_solo_el_periodo_y_no_la_suma_historica():
    periodos = [
        Periodo(1, P, date(2022, 1, 1), date(2023, 1, 1), D("700"), D("2.10")),
        Periodo(1, P, date(2023, 1, 1), date(2024, 1, 1), D("545"), D("4.50")),
        Periodo(1, P, date(2024, 1, 1), date(2025, 1, 1), D("550"), D("4.50")),
        Periodo(1, P, date(2025, 1, 1), date(2026, 1, 1), D("550"), D("4.50")),
        Periodo(1, P, date(2026, 1, 1), date(2027, 1, 1), D("550"), D("4.50")),
    ]
    assert cargo_recibo(periodos, date(2025, 3, 1), date(2025, 4, 1)) == D("4.50")
    assert cargo_recibo(periodos, date(2025, 1, 1), date(2026, 1, 1)) == D("54.00")
    # Recibo que cruza de un período a otro: dic-2025 + ene-2026
    assert cargo_recibo(periodos, date(2025, 12, 1), date(2026, 2, 1)) == D("9.00")
    assert sum(p.precio for p in periodos) == D("20.10")   # solo referencial
 
 
def test_particular_paga_cero_aunque_haya_balance():
    p, _ = crear_periodo(
        cliente_id=2, es_empresa=False, producto=P,
        desde=date(2026, 1, 1), hasta=date(2027, 1, 1),
        balance=D("550"), tarifas=TARIFAS,
    )
    assert p.precio_mostrado == D("0.00") and p.tarifa is None
    assert cargo_recibo([p], date(2026, 3, 1), date(2026, 4, 1)) == D("0.00")
    assert recalcular_periodo(p, TARIFAS).precio_mostrado == D("0.00")
 
 
def test_particular_sin_balance_ni_tarifa_no_falla():
    p, _ = crear_periodo(
        cliente_id=2, es_empresa=False, producto=P,
        desde=date(2026, 1, 1), hasta=date(2027, 1, 1),
        balance=D("0"), tarifas=[],
    )
    assert p.precio == D("0")
 
 
def test_ca08_registrar_historico_2022_con_formula_anterior():
    p, _ = crear_periodo(
        cliente_id=1, es_empresa=True, producto=P,
        desde=date(2022, 1, 1), hasta=date(2023, 1, 1),
        balance=D("700.00"), tarifas=TARIFAS, formula="proporcional",
    )
    assert p.precio_mostrado == D("2.10")
    # y con la fórmula vigente el mismo balance da 4.50
    n, _ = crear_periodo(
        cliente_id=1, es_empresa=True, producto=P,
        desde=date(2022, 1, 1), hasta=date(2023, 1, 1),
        balance=D("700.00"), tarifas=TARIFAS,
    )
    assert n.precio_mostrado == D("4.50")
    assert recalcular_periodo(p, TARIFAS).precio_mostrado == D("2.10")
 
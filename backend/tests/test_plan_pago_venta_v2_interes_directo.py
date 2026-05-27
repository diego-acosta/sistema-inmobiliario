from decimal import Decimal
from sqlalchemy import text
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_event_venta_confirmada import _vincular_comprador_venta
from tests.test_plan_pago_venta_v2_cuotas_iguales import _insertar_venta_minima

URL = "/api/v1/ventas/{id_venta}/plan-pago-v2/interes-directo"

def _payload():
    return {"monto_total_plan":1000.00,"moneda":"ARS","cantidad_cuotas":3,"tasa_interes_directo":0.10,"fecha_primer_vencimiento":"2026-06-10","periodicidad":"MENSUAL","regla_redondeo":"ULTIMA_CUOTA"}

def _rows(db_session,id_venta:int):
    return db_session.execute(text("""
    SELECT o.numero_obligacion,o.importe_total,co.orden_composicion,co.importe_componente,cf.codigo_concepto_financiero
    FROM relacion_generadora rg
    JOIN obligacion_financiera o ON o.id_relacion_generadora=rg.id_relacion_generadora AND o.deleted_at IS NULL
    JOIN composicion_obligacion co ON co.id_obligacion_financiera=o.id_obligacion_financiera AND co.deleted_at IS NULL
    JOIN concepto_financiero cf ON cf.id_concepto_financiero=co.id_concepto_financiero
    WHERE rg.tipo_origen='venta' AND rg.id_origen=:id_venta AND rg.deleted_at IS NULL
    ORDER BY o.numero_obligacion, co.orden_composicion
    """),{"id_venta":id_venta}).mappings().all()

def test_interes_directo_happy_path(client, db_session):
    id_venta=_insertar_venta_minima(db_session,codigo_venta='V-PPV2-ID-001')
    _vincular_comprador_venta(db_session,id_venta=id_venta)
    r=client.post(URL.format(id_venta=id_venta),headers=HEADERS,json=_payload())
    assert r.status_code==200, r.text
    data=r.json()['data']
    assert data['plan_pago_venta']['metodo_plan_pago']=='INTERES_DIRECTO'
    rows=_rows(db_session,id_venta)
    assert len(rows)==6
    assert [x['importe_total'] for x in rows if x['orden_composicion']==1]==[Decimal('366.66'),Decimal('366.66'),Decimal('366.68')]
    assert sum((x['importe_componente'] for x in rows if x['codigo_concepto_financiero']=='INTERES_FINANCIERO'),start=Decimal('0'))==Decimal('100.00')


def test_interes_directo_headers_requeridos(client, db_session):
    id_venta=_insertar_venta_minima(db_session,codigo_venta='V-PPV2-ID-002')
    _vincular_comprador_venta(db_session,id_venta=id_venta)
    r=client.post(URL.format(id_venta=id_venta),json=_payload())
    assert r.status_code==400

"""
Streamlit custom component wrapper: MapLibre GL JS regional map.

- ไม่ต้อง build (ไม่มี npm): ใช้ components/region_map/index.html ตรง ๆ
- JS โหลด MapLibre GL JS 4.7.1 จาก CDN (jsDelivr) -> เบราว์เซอร์ต้องออกอินเทอร์เน็ตได้
- ขอบเขตภูมิภาคมาจาก assets/thailand_regions.geojson ตามการแบ่ง 5 / 7 ภาคของปีนั้น
  (ใช้ _load_regional_geojson เดิมใน src/charts.py แล้วลดความละเอียดเพื่อลดขนาดข้อมูล)
"""
import math
from functools import lru_cache
from pathlib import Path

import streamlit.components.v1 as components

_COMPONENT_DIR = (
    Path(__file__).resolve().parent.parent / "components" / "region_map"
)

_region_map = components.declare_component(
    "thailand_region_map",
    path=str(_COMPONENT_DIR),
)

SIMPLIFY_TOLERANCE_DEG = 0.01   # ~1 กม. พอสำหรับแผนที่ระดับภูมิภาค
COORD_DECIMALS = 4


def _round_coords(value, digits=COORD_DECIMALS):
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], (int, float)):
            return [round(float(value[0]), digits), round(float(value[1]), digits)]
        return [_round_coords(item, digits) for item in value]
    return value


@lru_cache(maxsize=2)
def get_region_geojson(group):
    """GeoJSON ภูมิภาคแบบเบา (group = 5 หรือ 7). คืน None ถ้าอ่านไม่ได้/ไม่มี shapely."""
    from src.charts import _load_regional_geojson

    loaded = _load_regional_geojson(int(group))
    if loaded is None:
        return None

    try:
        from shapely.geometry import mapping
    except ImportError:
        return None

    _, polygons = loaded
    features = []

    for name, geometry in polygons.items():
        light = geometry.simplify(
            SIMPLIFY_TOLERANCE_DEG, preserve_topology=True
        )
        if light.is_empty:
            light = geometry
        shape = mapping(light)
        features.append({
            "type": "Feature",
            "properties": {"region": str(name)},
            "geometry": {
                "type": shape["type"],
                "coordinates": _round_coords(shape["coordinates"]),
            },
        })

    return {"type": "FeatureCollection", "features": features}


def _clean_number(value, digits=4):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if math.isfinite(number) else None


def render_region_map(
    *,
    year,
    values,
    details,
    metric_key,
    metric_label,
    selected,
    ack_seq,
    period_label,
    note="",
    height=620,
    key="thailand_region_map",
):
    """
    วาดแผนที่ MapLibre. คืนค่า event ล่าสุดจากผู้ใช้ (dict) หรือ None:
        {'type': 'select', 'region': <ชื่อภาค>, 'seq': <int>}
        {'type': 'clear', 'seq': <int>}
    ใช้ key คงที่ + ตำแหน่งคงที่ในหน้า เพื่อให้ iframe/แผนที่ไม่ถูกสร้างใหม่ระหว่าง rerun
    """
    group = 7 if int(year) >= 2568 else 5
    geo = get_region_geojson(group)

    if geo is None:
        return None, False

    event = _region_map(
        geo=geo,
        geo_id=f"g{group}",
        values={str(k): _clean_number(v) for k, v in values.items()},
        details={
            str(region): {
                str(metric): _clean_number(number)
                for metric, number in row.items()
            }
            for region, row in details.items()
        },
        metric_key=str(metric_key),
        metric_label=str(metric_label),
        selected=selected,
        ack_seq=int(ack_seq),
        period_label=str(period_label),
        note=str(note or ""),
        height=int(height),
        key=key,
        default=None,
    )
    return event, True
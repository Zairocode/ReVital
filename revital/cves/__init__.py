"""ReVital - evaluacion: inventarios -> CVE (NVD) -> CISA KEV -> prioridad -> reporte por entidad.

Solo stdlib, compatible con Python 3.8+ (Windows 7). Funciona offline con los catalogos de datos/.
Uso: python -m revital.cves --out salida          (lee salida/inventario-*.json)
     python -m revital.cves --demo                (caso portal-muni-gt con datos de ejemplo)
     python -m revital.cves --actualizar          (descarga KEV y NVD; requiere internet)
"""

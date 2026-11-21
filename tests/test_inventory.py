"""Contrato: dos objetivos del mismo tipo no se pisan. Correr: python tests/test_inventory.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from revital import inventory

assert inventory.slug("http://localhost:8080/") == "localhost-8080"
assert inventory.slug("C:\\inetpub\\app") == "c-inetpub-app"
assert inventory.slug("10.0.0.0/24") == "10-0-0-0-24"

out = tempfile.mkdtemp()
a = inventory.nuevo("web", "http://portal1.gob", "MUNI")
b = inventory.nuevo("web", "http://portal2.gob", "MUNI")
a["components"].append(inventory.componente("Apache", "2.4.49", "header server", "x"))
pa, pb = inventory.guardar(a, out), inventory.guardar(b, out)
assert pa != pb and len(os.listdir(out)) == 2, os.listdir(out)
inventory.guardar(a, out)  # mismo objetivo: actualiza, no duplica
assert len(os.listdir(out)) == 2
todos = inventory.cargar_todos(out)
assert sorted(i["target"] for i in todos) == ["http://portal1.gob", "http://portal2.gob"]
print("ok")

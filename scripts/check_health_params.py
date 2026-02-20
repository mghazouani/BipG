import xmlrpc.client
url = "http://odoo:8069"
db, user, pw = "odoo", "admin", "admin"
uid = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common").authenticate(db, user, pw, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
ids = models.execute_kw(db, uid, pw, "ir.config_parameter", "search", [[("key", "ilike", "liv.")]])
recs = models.execute_kw(db, uid, pw, "ir.config_parameter", "read", [ids], {"fields": ["key", "value"]})
for r in recs:
    masked = "***MASKED***" if "secret" in r["key"].lower() else r["value"]
    print(f"PARAM:: {r['key']} = {masked}")

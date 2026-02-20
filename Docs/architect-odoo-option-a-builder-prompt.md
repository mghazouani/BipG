# Architect: analyse Odoo Option A + prompt Builder

## 1) Analyse du spec

### Cohérence avec l’existant
- **Pas de nouveau modèle** : usage de `ir.config_parameter` uniquement → aligné avec la contrainte “simple, peu de custom”.
- **Abstract model** `liv.backend.health` : pas de table, pas de sécurité à gérer, pas de `ir.model.access.csv` → correct.
- **Cron** : timeout 5s, pas de secret en log → bon pour la prod.

### Points validés
- **Menu parent** : dans `liv_delivery/views/delivery_views.xml` le menu racine LIV est `id="menu_liv_root"`. Le sous-menu “Backend Status” doit avoir `parent="menu_liv_root"`.
- **Paramètres** : `liv.fastapi_base_url`, `liv.health_secret`, `liv.backend_health_status`, `liv.backend_health_updated`, `liv.backend_health_message` → noms clairs et préfixés.

### Ajustements recommandés

1. **Cron – `model_id`**  
   Le spec propose `model_id ref="base.model_ir_actions_server"` alors que le code exécuté est `env['liv.backend.health'].liv_check_backend_health()`. En Odoo 17, pour un cron de type “code”, `model_id` doit pointer vers le modèle dont on appelle la méthode. À utiliser :  
   `model_id ref="liv_delivery.model_liv_backend_health"`  
   et dans `code` :  
   `model.liv_check_backend_health()`  
   (pour un AbstractModel, `model` est bien un recordset du modèle, et la méthode `@api.model` fonctionne).  
   Si au chargement des data la ref `liv_delivery.model_liv_backend_health` n’existe pas (selon version Odoo), fallback : garder `env['liv.backend.health'].liv_check_backend_health()` et `model_id ref="base.model_ir_config_parameter"` (ou autre modèle inerte) uniquement pour satisfaire le champ requis.

2. **Cron – champs Odoo 17**  
   Vérifier que le cron utilise les champs attendus par Odoo 17 (`state`, `code`, etc.). Certaines versions utilisent `ir.cron` avec un champ `code` direct, d’autres délèguent à `ir.actions.server`. Le Builder devra coller à la structure réelle de `ir.cron` dans la version cible.

3. **`ts` côté FastAPI**  
   `ts` est maintenant renvoyé par FastAPI en **ISO-8601 UTC** (suffixe `Z`). Le code Python qui fait `PARAM_UPDATED = ts` peut donc stocker directement cette string.

4. **Dépendance `requests`**  
   Odoo inclut souvent `requests` (ou `urllib3`). Si l’image n’a pas `requests`, fallback : `urllib.request` (stdlib) pour une seule GET avec timeout, ou ajouter `requests` en dépendance du module / de l’image. Le Builder peut implémenter en `requests` puis documenter le fallback si besoin.

### Risques
- **Faible** : cron mal configuré (mauvais `model_id` ou champ manquant) → erreur au chargement des data ou à l’exécution. Mitigation : tester “Run Manually” après upgrade du module.
- **Faible** : base_url ou secret mal configurés → statut “down” ou “auth_error”. Mitigation : doc des paramètres (Settings > Technical > System Parameters).

### Data impacts
- **Odoo** : aucun nouveau modèle persistant ; lecture/écriture de `ir.config_parameter` via `sudo()`. Nouvelles données : 1 enregistrement `ir.cron`, 1 action `ir.actions.act_window`, 1 `menuitem`.

### Test strategy
- **Odoo** : pas de test unitaire obligatoire pour ce premier pas ; validation manuelle : upgrade module, définir `liv.fastapi_base_url` et `liv.health_secret`, lancer le cron à la main, vérifier les paramètres `liv.backend_health_*` et l’entrée de menu “Backend Status”.

---

## 2) Prompt à donner au Builder

Copier-coller le bloc suivant à l’agent Builder.

---

**Odoo Option A — LIV Backend Health (cron + vue)**

Implémenter le suivi du health du backend FastAPI dans l’addon Odoo `liv_delivery` : un cron appelle `/health/status`, stocke le résultat dans `ir.config_parameter`, et une entrée de menu ouvre les paramètres LIV.

**Contraintes**
- Aucun nouveau modèle (table) : uniquement `ir.config_parameter` et un modèle abstrait.
- Ne pas modifier `.env` ni secrets ; ne pas logger le secret.
- Respecter le repo : uniquement des fichiers sous `liv-poc/odoo-addon/liv_delivery/`.

**Fichiers à créer**

1. **`liv-poc/odoo-addon/liv_delivery/models/backend_health.py`**  
   - Modèle abstrait `liv.backend.health` (`_name = "liv.backend.health"`, `_description = "LIV Backend Health (FastAPI) - no DB model; config-based"`).
   - Constantes : `PARAM_BASE_URL = "liv.fastapi_base_url"`, `PARAM_SECRET = "liv.health_secret"`, `PARAM_STATUS = "liv.backend_health_status"`, `PARAM_UPDATED = "liv.backend_health_updated"`, `PARAM_MESSAGE = "liv.backend_health_message"`.
   - Méthodes : `_get_param(key, default="")` et `_set_param(key, value)` via `ir.config_parameter.sudo()`.
   - Méthode `liv_check_backend_health(self)` (appelée par le cron) :
     - Lire base_url et secret ; si base_url vide, set status “down”, message “Missing liv.fastapi_base_url” et return.
     - GET `{base_url}/health/status` avec header `Authorization: Bearer {secret}` si secret, timeout 5 secondes (ex. `requests.get`).
     - En cas d’exception réseau : status “down”, message “Connection error: {type(e).__name__}”, ne pas logger le secret.
     - HTTP 401 : status “auth_error”, message “Unauthorized (check liv.health_secret)”.
     - Sinon parser le JSON ; si échec : status “down”, message “Invalid JSON response (HTTP …)”.
     - À partir du JSON : `ok`, `redis`, `odoo`, `ts`, `message`. Règles : si HTTP 200 et ok et redis et odoo → status “ok” ; sinon si (redis ou odoo) → “degraded” ; sinon “down”. Enregistrer dans les paramètres : PARAM_STATUS, PARAM_UPDATED (ts), PARAM_MESSAGE.
     - Logger uniquement status, redis, odoo, http (pas le secret).

2. **`liv-poc/odoo-addon/liv_delivery/data/backend_health_cron.xml`**  
   - `noupdate="1"`.
   - Un enregistrement `ir.cron` : nom “LIV: Check Backend Health”, intervalle 5 minutes, numbercall -1, active True.
   - Pour l’exécution : soit `model_id ref="liv_delivery.model_liv_backend_health"` avec `code` = `model.liv_check_backend_health()`, soit si la ref du modèle abstrait n’est pas disponible au chargement, utiliser `code` = `env['liv.backend.health'].liv_check_backend_health()` et un `model_id` de fallback (ex. `base.model_ir_config_parameter`). Adapter aux champs réels de `ir.cron` de ta version Odoo (Odoo 17 : vérifier la doc ou le schéma).

3. **`liv-poc/odoo-addon/liv_delivery/views/backend_health_views.xml`**  
   - Une action `ir.actions.act_window` : name “LIV Backend Status”, `res_model` = `ir.config_parameter`, view_mode tree,form, domain `[('key', 'ilike', 'liv.%')]`, context éventuel pour filtre par défaut sur “liv.”.
   - Un menuitem : name “Backend Status”, **parent = `menu_liv_root`** (l’ID du menu racine LIV est bien `menu_liv_root` dans `delivery_views.xml`), action = l’action ci-dessus, sequence 90.

**Fichiers à modifier**

4. **`liv-poc/odoo-addon/liv_delivery/models/__init__.py`**  
   - Ajouter : `from . import backend_health`

5. **`liv-poc/odoo-addon/liv_delivery/__manifest__.py`**  
   - Dans la liste `data`, ajouter (dans l’ordre souhaité) :  
     `'data/backend_health_cron.xml'`,  
     `'views/backend_health_views.xml'`.

**Config utilisateur (documentation, pas à coder)**  
Après mise à jour du module, dans Paramètres > Technique > Paramètres > Paramètres système :  
- `liv.fastapi_base_url` = ex. `http://fastapi:8000`  
- `liv.health_secret` = même valeur que `HEALTH_SECRET` côté FastAPI  

**Livrables**
- Résumé des changements.
- Liste des fichiers créés/modifiés.
- Commande(s) suggérées pour upgrade du module (à valider par l’utilisateur).

---

**Fin du prompt Builder**

---

## Summary

- Le spec Option A est cohérent ; le menu parent correct est **`menu_liv_root`** (confirmé dans `delivery_views.xml`).
- Ajustements à transmettre au Builder : cron avec `model_id` sur `liv.backend.health` et `code` = `model.liv_check_backend_health()`, ou fallback avec `env['liv.backend.health']` si la ref du modèle abstrait pose problème ; pas de nouveau modèle ; pas de log du secret.
- Le document ci-dessus contient l’analyse Architect et le **prompt prêt à copier-coller** pour l’agent Builder.

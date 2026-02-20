# Revue Reviewer Option A — Analyse et prompt Builder

## 1) Analyse des findings

| Priorité | Finding | Décision |
|----------|---------|----------|
| **High** | Exposition de `liv.health_secret` dans la vue « Backend Status » (action sur `ir.config_parameter` avec domaine `liv.%`) | **À corriger** : ne plus ouvrir `ir.config_parameter` pour ce menu. Introduire un modèle transient en lecture seule qui expose uniquement `status`, `updated`, `message`, `base_url` (jamais le secret). Le menu « Backend Status » ouvre ce modèle (via action serveur qui crée un enregistrement puis ouvre le formulaire). |
| **Medium** | `HTTPError` : `e.fp` lu sans fermeture explicite → fuite ressource possible | **À corriger** : dans le bloc `except HTTPError`, fermer `e.fp` dans un `finally` après lecture du corps. |
| **Medium** | SSRF possible via `liv.fastapi_base_url` | **POC : accepté**. Documenter en commentaire ou doc ; durcissement (liste d’hôtes / schéma) en prod plus tard si besoin. |
| **Low** | Log après 401 : homogénéiser avec `http=401` | **Déjà fait** dans le code actuel (`http=401` dans le log). Rien à faire. |
| **Low** | Cron enregistré sur `ir.config_parameter` mais exécute `liv.backend.health` | **Documenter** : ajouter un court commentaire dans le cron XML ou dans la doc du module. |

**Résumé**  
- À faire en priorité : (1) Vue dédiée sans secret (transient + action + formulaire), (2) Fermeture de `e.fp` dans `HTTPError`.  
- Optionnel : commentaire SSRF pour plus tard ; commentaire cron pour la doc.

---

## 2) Prompt Builder — Étapes à exécuter

Copier-coller le bloc suivant à l’agent Builder.

---

**Mission : Appliquer les correctifs de la revue Option A (LIV Backend Health)**

Contexte : la revue a identifié une exposition du secret (`liv.health_secret`) dans la vue « Backend Status » et une fuite de ressource possible sur `HTTPError`. Tu dois appliquer les correctifs ci-dessous **dans l’ordre**, en ne modifiant que les fichiers listés. Pas de changement de .env ni de secrets. Repo : `liv-poc/odoo-addon/liv_delivery/`.

---

### Étape 1 — Ne plus exposer le secret : modèle transient + vue dédiée

**Objectif** : Le menu « Backend Status » ne doit plus ouvrir `ir.config_parameter`. Il doit ouvrir une vue en lecture seule qui affiche uniquement : statut du backend, date de mise à jour, message optionnel, base URL (sans jamais afficher `liv.health_secret`).

1. **Fichier `models/backend_health.py`**  
   - Ajouter un **second modèle** (après la classe `LivBackendHealth`), **TransientModel** :
     - `_name = "liv.backend.health.display"`
     - `_description = "LIV Backend Health status (read-only)"`
   - Champs (tous en lecture seule) :
     - `status` = `fields.Char(readonly=True)`
     - `updated` = `fields.Char(readonly=True)` (ex. timestamp ou ISO)
     - `message` = `fields.Text(readonly=True)`
     - `base_url` = `fields.Char(readonly=True)` (pour info, pas le secret)
   - Méthode **`_get_display_values()`** (sans paramètre `self` utile, peut être `@api.model` sur le TransientModel) : lit avec `self.env["ir.config_parameter"].sudo().get_param(...)` les clés `PARAM_STATUS`, `PARAM_UPDATED`, `PARAM_MESSAGE`, `PARAM_BASE_URL` (ne **jamais** lire ni retourner `PARAM_SECRET`). Retourne un dict `{"status": ..., "updated": ..., "message": ..., "base_url": ...}`.
   - Méthode **`@api.model`** **`get_display_record()`** : appelle `_get_display_values()`, fait `self.create(vals)` avec ce dict, retourne l’enregistrement créé (pour que l’action serveur puisse ouvrir ce record).

2. **Fichier `views/backend_health_views.xml`**  
   - **Supprimer** l’action actuelle qui ouvre `ir.config_parameter` (res_model `ir.config_parameter`, domaine `liv.%`).
   - **Ajouter** :
     - Une **vue formulaire** pour `liv.backend.health.display` : champs `status`, `updated`, `message`, `base_url` (tous en readonly). Pas de champ secret. Optionnel : un bouton « Actualiser » qui appelle une méthode qui recrée un record via `get_display_record()` et rouvre le formulaire (ou simple texte « Les valeurs sont lues au moment de l’ouverture »).
     - Une **action fenêtre** `ir.actions.act_window` pour ouvrir le formulaire de `liv.backend.health.display` (view_mode form, res_model `liv.backend.health.display`). On l’utilisera avec un `res_id` fourni par l’action serveur.
     - Une **action serveur** `ir.actions.server` :
       - Déclenchée par le menu (state = code).
       - Code Python : `record = env['liv.backend.health.display'].get_display_record()` puis retourner un **dict** d’action fenêtre pour ouvrir ce record en formulaire : `{'type': 'ir.actions.act_window', 'name': '...', 'res_model': 'liv.backend.health.display', 'res_id': record.id, 'view_mode': 'form'}` (et éventuellement `view_id` si une vue form spécifique est définie). Ainsi l’utilisateur voit directement le formulaire avec les valeurs lues depuis `ir.config_parameter` (sans secret).
     - Le **menuitem** « Backend Status » (parent `menu_liv_root`, sequence 90) doit appeler cette **action serveur** (et non plus l’ancienne action sur `ir.config_parameter`).

   Ainsi, tout utilisateur ayant accès au menu « Backend Status » ne voit que status/updated/message/base_url, jamais le secret.

3. **Sécurité**  
   - Fichier `security/ir.model.access.csv` : ajouter une ligne pour le modèle `liv.backend.health.display` (groupe à ta convenance, ex. `base.group_system`), avec au minimum les droits de lecture (et création/suppression pour que l’action serveur puisse créer un enregistrement transient). Exemple : `access_liv_backend_health_display,...,1,1,1,1` (à adapter au format exact du fichier).

4. **Manifest**  
   - Aucun nouveau fichier data à ajouter si tout reste dans `views/backend_health_views.xml`. Vérifier que ce fichier est bien listé dans `__manifest__.py` sous `data`.

---

### Étape 2 — Fermer `e.fp` en cas de `HTTPError`

**Fichier `models/backend_health.py`**  
Dans le bloc `except HTTPError as e:` :

- Lire le corps et le code comme aujourd’hui (`status_code = e.code`, `body = e.fp.read()...` si `e.fp`).
- **Ensuite**, dans un bloc `finally` (ou un `try/finally` autour de la lecture), **fermer** `e.fp` si présent :  
  `if getattr(e, "fp", None) is not None: try: e.fp.close(); except Exception: pass`  
  pour éviter de laisser un file-like ouvert.

Exemple de structure (à adapter à ton style) :

```python
except HTTPError as e:
    try:
        status_code = e.code
        body = (e.fp.read().decode("utf-8", errors="replace") if e.fp else "")
    finally:
        if getattr(e, "fp", None) is not None:
            try:
                e.fp.close()
            except Exception:
                pass
```

Le reste du traitement (401, JSON, status down/degraded/ok) reste inchangé.

---

### Étape 3 — Documentation / commentaires (optionnel)

- Dans `data/backend_health_cron.xml` (ou en commentaire dans `backend_health.py`), ajouter une courte note : le cron est enregistré sur un modèle « porteur » (ex. `ir.config_parameter` ou celui utilisé) mais exécute en réalité `env['liv.backend.health'].liv_check_backend_health()`.
- Dans `backend_health.py`, un court commentaire peut rappeler que `liv.fastapi_base_url` est contrôlé par l’admin (risque SSRF en cas de config erronée ; durcissement possible en prod).

---

### Livrables attendus

- Liste des fichiers modifiés (avec résumé des changements).
- Confirmation que le menu « Backend Status » ouvre bien la vue dédiée (transient) et que `liv.health_secret` n’apparaît nulle part dans cette vue.
- Commandes suggérées pour mise à jour du module (ex. `-u liv_delivery`) à valider par l’utilisateur.

---

**Fin du prompt Builder**

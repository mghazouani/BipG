# Revue — Suivi Option A (itération 2) : analyse + prompt Builder

## 1) Analyse des findings

### Medium — Bug `headers or None` (cron crash sans secret)
- **Constat** : dans `models/backend_health.py`, la ligne `Request(url, headers=headers or None)` passe `None` quand `headers == {}` (secret vide). `urllib.request.Request` itère `headers.items()` → crash.
- **Fix** : toujours passer le dict (même vide). `Request(..., headers={})` est valide.

### Low — Duplication `URLError` / `Exception`
- **Constat** : deux branches strictement identiques.
- **Fix recommandé** : fusionner en un seul bloc `except Exception as e:` (URLError est déjà un sous-type).
- **Alternative** : garder séparé si intention future (ex. message spécifique timeout), mais alors commenter l’intention.

### Low — `<p>` directement sous `<sheet>`
- **Constat** : OK en Odoo 16/17, mais pour compat multi-version, plus sûr d’envelopper dans un `<div>` ou un `<group>`.
- **Fix** : remplacer le `<p>` par un `<div class="text-muted">…</div>` (ou mettre le texte dans un `<group>`).

---

## 2) Prompt Builder — Correctifs itération 2 (delta)

Copier-coller à l’agent Builder.

---

**Objectif** : corriger le crash du cron quand `liv.health_secret` est vide, et appliquer deux petits cleanups (lisibilité + compat XML), sans changer la logique fonctionnelle.

### A) Fix critique : `Request(..., headers=headers or None)` → toujours passer le dict

**Fichier** : `liv-poc/odoo-addon/liv_delivery/models/backend_health.py`

- Modifier la création de `Request` :
  - Avant : `req = Request(url, headers=headers or None)`
  - Après : `req = Request(url, headers=headers)`

Justification : un dict vide est accepté ; `None` fait crasher `Request`.

### B) Cleanup : fusionner les except identiques (URLError/Exception)

**Fichier** : `liv-poc/odoo-addon/liv_delivery/models/backend_health.py`

- Remplacer les deux blocs identiques :
  - `except URLError as e: ... return`
  - `except Exception as e: ... return`
- Par un seul bloc :

```python
except Exception as e:
    self._set_param(PARAM_STATUS, "down")
    self._set_param(PARAM_MESSAGE, "Connection error: %s" % type(e).__name__)
    self._set_param(PARAM_UPDATED, "")
    _logger.info(
        "liv_backend_health status=down message=Connection error: %s",
        type(e).__name__,
    )
    return
```

Si tu préfères garder 2 branches pour différencier plus tard, ajoute un commentaire “intentionnel” et laisse tel quel.

### C) Compat vue : remplacer `<p>` sous `<sheet>` par `<div>`

**Fichier** : `liv-poc/odoo-addon/liv_delivery/views/backend_health_views.xml`

- Remplacer :

```xml
<p class="text-muted">
    Les valeurs ...
</p>
```

- Par :

```xml
<div class="text-muted">
    Les valeurs ...
</div>
```

### D) Validation rapide (tests manuels / checks)

1. **Sans secret** : supprimer/vider `liv.health_secret` puis exécuter le cron manuellement → **pas de crash**, statut mis à jour.
2. **401** : mettre un mauvais secret → `liv.backend_health_status = auth_error`, message “Unauthorized…”.
3. **Vue** : ouvrir `LIV > Backend Status` → dialog avec `status/updated/base_url/message`, aucun secret affiché.

### Livrables
- Résumé des changements
- Fichiers modifiés
- Commandes suggérées pour upgrade du module (à valider par l’utilisateur)

---

**Fin du prompt Builder**


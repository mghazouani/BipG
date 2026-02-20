# Revue — Itération 3 : prompt Builder (cleanup import URLError)

## Constat
- Le code est validé fonctionnellement.
- Il reste un seul finding **Low** : import `URLError` inutilisé dans `backend_health.py` (risque warning CI lint type F401 unused-import).

---

## Prompt Builder — Correctif itération 3 (cosmétique)

Copier-coller à l’agent Builder.

---

**Objectif** : supprimer l’import mort `URLError` (aucun changement fonctionnel).

### Étape 1 — Nettoyer l’import

**Fichier** : `liv-poc/odoo-addon/liv_delivery/models/backend_health.py`

- Avant :

```python
from urllib.error import URLError, HTTPError
```

- Après :

```python
from urllib.error import HTTPError
```

### Étape 2 — Validation rapide

- Vérifier que le module se charge toujours (upgrade Odoo).
- Rejouer un cron manuellement (avec et sans secret) : comportement inchangé.

### Livrables
- Résumé
- Fichiers modifiés
- Commandes suggérées (upgrade module) **à faire valider par l’utilisateur**

---

**Fin du prompt Builder**


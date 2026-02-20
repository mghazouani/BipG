A. Odoo (UI)

- [x] Créer une mission liv.delivery → nom auto LIV/000x *(E2E : POST /poc/seed/delivery)*
- [x] Assigner un driver_id *(E2E : seed avec driver_id=2)*
- [x] Changer les états via **boutons Odoo** : draft → assigned → en_route → arrived → delivered *(manuel OK)*
- [x] Annuler depuis n'importe quel état autorisé → cancelled *(manuel OK)*
- [x] Voir l'onglet "Tracking Snapshots" et les lignes s'ajouter *(manuel OK)*

B. FastAPI (REST) — **validé par E2E**

- [x] GET /drivers/{driver_id}/active-mission retourne la mission active correcte
- [x] POST /deliveries/{delivery_id}/state modifie bien l'état dans Odoo
- [x] GET /deliveries/{delivery_id} retourne la mission + last position Redis (redis_last)

C. FastAPI (WS) + Redis — **validé**

- [x] Envoi WS (delivery_id) → ack
- [x] Redis track:last:<delivery_id> existe et TTL ≈ 1h
- [x] PubSub track:channel:<delivery_id> reçoit les events

D. Snapshot Odoo + last_* — **validé par E2E**

- [x] Après 60s d'envoi tracking :
  - [x] Au moins une ligne liv.delivery.track créée *(E2E : GET /deliveries/{id}/snapshots, count ≥ 1)*
  - [x] liv.delivery.last_lat/last_lon/last_ts mis à jour *(E2E : GET /deliveries/{id})*

---

## Checklist de validation A.1 ✅

**WebSocket validation**
- [x] Sans `driver_id` → erreur + close 1008
- [x] `driver_id != delivery.driver_id` → erreur + close 1008
- [x] `state` hors (assigned / en_route / arrived) → erreur + close 1008

**Throttling**
- [x] 2 messages &lt; 10s → 2ᵉ `rate_limited`, pas d’écriture Redis/Odoo
- [x] Après ~11s → message accepté

**Résilience Odoo**
- [x] Si Odoo indisponible : WS continue + Redis continue
- [x] Quand Odoo revient : queue drain + snapshots reprennent (logs `odoo_write_ok`)
- [x] Si spam : `queue_drop` loggé au-delà de `ODOO_QUEUE_MAX`

**Observabilité**
- [x] logs : `ws_connected` / `ws_rejected` / `rate_limited` / `odoo_write_fail` / `odoo_write_ok` / `queue_drop`

---

## Checklist de validation A.2 ✅

**WebSocket token auth**
- [x] `/ws/track` exige `?token=<token>` en query
- [x] Token HMAC : `base64(driver_id:delivery_id:timestamp:signature)` avec `WS_SECRET`
- [x] Token invalide ou expiré (&gt; 5 min) → close 1008 + log `ws_rejected(reason="invalid_token")`

**Cache Redis (delivery ↔ driver)**
- [x] Validation Odoo OK → stockage `delivery:driver:<delivery_id>` = driver_id, TTL 600s
- [x] Odoo indisponible : validation via Redis ; absent ou mismatch → rejet WS

**Reprise Odoo**
- [x] Au retour Odoo : première validation réussie rafraîchit le cache Redis

**Config**
- [x] `WS_SECRET` requis (démarrage refusé si absent)
- [x] `WS_TOKEN_MAX_AGE_SECONDS` (défaut 300), `DELIVERY_DRIVER_CACHE_TTL` (défaut 600)

**E2E**
- [x] Génération token HMAC côté script
- [x] Test négatif : token invalide → rejet
- [x] Rate limit et snapshots toujours validés

---

## Checklist de validation A.3 ✅

**Rotation secret WS**
- [x] `WS_SECRET_PREV` optionnel (env)
- [x] Token accepté si signé par `WS_SECRET` ou `WS_SECRET_PREV`
- [x] Logs `ws_token_verified(secret="current")` / `ws_token_verified(secret="prev")` (sans logger les secrets)

**Anti-replay / skew**
- [x] Token trop vieux → `token_expired` + close 1008
- [x] Token dans le futur &gt; `WS_TOKEN_MAX_FUTURE_SKEW_SECONDS` → `token_in_future` + close 1008
- [x] Raisons loggées : `invalid_token_format`, `invalid_signature`, `token_expired`, `token_in_future`

**CORS**
- [x] `ALLOWED_ORIGINS` (comma-separated), défaut localhost:3000, 5173
- [x] CORSMiddleware : allow_origins, allow_credentials true, allow_methods/headers [\"*\"]

**WebSocket Origin**
- [x] Si en-tête Origin présent et non dans ALLOWED_ORIGINS → rejet 1008, log `ws_rejected(reason="origin_not_allowed")`
- [x] Si Origin absent → autorisé (mobile / wscat)

**E2E**
- [x] Test token timestamp futur → rejet `token_in_future`
- [x] Test rotation : si `WS_SECRET_PREV` set, token avec prev accepté ; sinon skip avec message
- [x] Invalid token, rate limit, snapshots inchangés

---

## Résultats E2E (dernier run)

`python scripts/test_e2e_option_a.py` : **tous les steps (a), (b), (b2), (b3), (b4 si WS_SECRET_PREV), (c0), (c), (d), (e), (f) PASS**.  
Création mission, active-mission, rejet token invalide (b2), rejet token futur (b3), rotation secret optionnelle (b4), rate limit, WS 70s, last_* + redis_last, snapshots, POST state. A.1 + A.2 + A.3 validés.

---

## Statut

**Option A DoD : tout validé** (E2E + tests manuels UI Odoo OK). **Hardening A.1, A.2 et A.3** : checklists validées, E2E passant.

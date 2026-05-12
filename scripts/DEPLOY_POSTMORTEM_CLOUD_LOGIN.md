# Cloud deploy postmortem (Azure Container Apps)

Aplikace je teď funkční, ale nejvíc času jsme ztratili na kombinaci několika chyb, které se tvářily jako „špatné heslo“.

## Hlavní příčiny

### 1) Frontend -> API routing přes ACA ingress (Host header + TLS)
- Nginx proxy původně neposílala správný host pro interní ACA routing.
- Bez správného hostu Envoy v ACA neuměl stabilně routovat request na správnou interní appku.
- Po přepnutí na HTTPS upstream bylo navíc potřeba zapnout SNI v nginx (`proxy_ssl_server_name on;` + `proxy_ssl_name $proxy_host;`), jinak docházelo k 502 / handshake resetu.

**Fix:**
- `proxy_set_header Host $proxy_host;`
- `proxy_ssl_server_name on;`
- `proxy_ssl_name $proxy_host;`

### 2) API -> Qdrant URL (interní FQDN + port)
- `QDRANT_URL` přes short hostname/HTTP bylo nespolehlivé (timeouts).
- `qdrant-client` měl při `https://<internal-fqdn>` bez explicitního portu timeouty.
- Stabilní konfigurace byla až s interním FQDN a explicitním `:443`.

**Fix:**
- `QDRANT_URL=https://<qdrant>.internal.<env-domain>:443`

### 3) „Login vypadá rozbitě“ byl sekundární symptom
- Protože API health padala na `qdrant: down`, login requesty často timeoutovaly nebo končily 499/5xx na proxy vrstvě.
- Navenek to působilo jako problém s heslem, ale root cause byla síť/routing konfigurace.

### 4) Hesla/hash confusion během seed/migrací
- Dříve se střídaly různé hodnoty demo hesel a bylo těžké poznat, co je aktuálně nasazené.
- Přidání fixed demo režimu + lepší persist deploy stavu výrazně zkrátilo troubleshooting.

## Finální stabilní stav
- Frontend proxyuje na API přes interní HTTPS FQDN.
- API i migrate job používají Qdrant interní HTTPS FQDN s `:443`.
- `/health` vrací `qdrant: up`.
- Login (`admin/admin123`) funguje přes veřejný frontend endpoint.

## Doporučení do budoucna
- U interní ACA komunikace preferovat interní FQDN (ne short host) pro kritické toky.
- U HTTPS upstreamu v nginx vždy explicitně řešit SNI.
- U Qdrant klienta držet explicitní URL včetně schématu a portu.
- Po deploy automaticky ověřovat:
  1. API `/health`
  2. Qdrant dostupnost z API kontejneru
  3. login end-to-end přes frontend

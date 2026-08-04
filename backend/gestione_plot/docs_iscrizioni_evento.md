# Iscrizioni evento PayPal — note operative

## Fonte di verità gameplay
`Evento.partecipanti` (M2M) è ciò che conta per premi, scommesse, report.
Un pagamento `CAPTURED` senza riga in `partecipanti` = **pagato ma non iscritto in gioco**.

## Bug storico (ultimo evento)
Possibili cause:
1. Capture PayPal OK ma finalize DB fallito → resta PENDING/FAILED senza M2M
2. Controllo «altro PG già iscritto» **dopo** la capture → soldi presi, stato FAILED, no M2M
3. Staff rimuove PG da partecipanti dopo il pagamento

## Fix in codice
- Controllo «altro PG» **prima** della capture PayPal
- Su `already_captured`: riallinea automaticamente `partecipanti`
- Comando riparazione: `python manage.py riallinea_iscrizioni_evento [--evento ID]`

```bash
# Docker
docker compose … exec -T backend python manage.py riallinea_iscrizioni_evento
docker compose … exec -T backend python manage.py riallinea_iscrizioni_evento --evento 42
```

# personaggi/services.py

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import sys

from .models import (
    Oggetto, Infusione, Mattone, Personaggio, OggettoInInventario, 
    TIPO_OGGETTO_FISICO, TIPO_OGGETTO_MOD, TIPO_OGGETTO_MATERIA, 
    TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE,
    COSTO_PER_MATTONE_OGGETTO, QrCode, OggettoStatistica, Inventario,
    OggettoBase, OggettoStatisticaBase, 
    ForgiaturaInCorso, Abilita, 
    OggettoCaratteristica, RichiestaAssemblaggio,
    STATO_RICHIESTA_PENDENTE, STATO_RICHIESTA_COMPLETATA, STATO_RICHIESTA_RIFIUTATA,
    TIPO_OPERAZIONE_FORGIATURA, TIPO_OPERAZIONE_RIMOZIONE, TIPO_OPERAZIONE_INSTALLAZIONE, TIPO_OPERAZIONE_INNESTO,
    TIPO_OGGETTO_AUMENTO, TIPO_OGGETTO_POTENZIAMENTO,
)

class GestioneOggettiService:
    
    @staticmethod
    def calcola_cog_utilizzata(pg: Personaggio):
        """Calcola la Capacità Oggetti (COG) occupata."""
        oggetti = pg.get_oggetti().filter()
        cog_totale = 0
        for obj in oggetti:
            if obj.tipo_oggetto in [TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE]:
                cog_totale += 1
            elif obj.tipo_oggetto == TIPO_OGGETTO_FISICO and obj.is_equipaggiato:
                cog_totale += 1
        return cog_totale

    @staticmethod
    def verifica_consenso(target: Personaggio, qrcode_id: str):
        try:
            qr = QrCode.objects.get(id=qrcode_id)
            if qr.vista and hasattr(qr.vista, 'personaggio') and qr.vista.personaggio == target:
                return True
            return False
        except QrCode.DoesNotExist:
            return False

    @staticmethod
    def equipaggia_oggetto(personaggio: Personaggio, oggetto: Oggetto):
        """Gestisce l'azione Equipaggia/Disequipaggia."""
        inv_corrente = oggetto.inventario_corrente
        if not inv_corrente or inv_corrente.id != personaggio.id:
             raise ValidationError(f"Non possiedi l'oggetto '{oggetto.nome}'.")
        
        if oggetto.is_equipaggiato:
            oggetto.is_equipaggiato = False
            oggetto.save()
            return "Disequipaggiato"
        
        cog_used = GestioneOggettiService.calcola_cog_utilizzata(personaggio)
        cog_max = personaggio.get_valore_statistica('COG')
        
        if cog_used >= cog_max:
             raise ValidationError(f"Capacità Oggetti raggiunta ({cog_used}/{cog_max}).")
        
        oggetto.is_equipaggiato = True
        oggetto.save()
        return "Equipaggiato"

    @staticmethod
    def crea_oggetto_da_infusione(infusione, proprietario, nome_personalizzato=None):
        """
        Factory method: crea fisicamente l'oggetto nel database.
        Logica aggiornata per usare i nuovi campi flessibili di Punteggio (Aura).
        """
        
        # 1. Determina l'Aura dell'Oggetto
        # Regola: Se infusione ha aura_infusione (secondaria), l'oggetto prende quella. Altrimenti la primaria.
        aura_oggetto = infusione.aura_infusione if infusione.aura_infusione else infusione.aura_richiesta

        # 2. Determina Categoria (Aumento vs Potenziamento)
        # Regola Utente: Se c'è uno slot corporeo definito nell'infusione, è un Aumento.
        # Altrimenti fallback sui flag dell'aura.
        #is_aumento = bool(infusione.slot_corpo_permessi) or aura_oggetto.produce_aumenti
        scelta = getattr(infusione, 'tipo_risultato', 'POT')
        
        tipo_oggetto = TIPO_OGGETTO_FISICO # Fallback
        
        tipo_oggetto = 'POT'
        prefisso_nome = "Oggetto"
        is_tecnologico = False
        slot_corpo_finale = None

        if scelta == 'AUM':
            # # --- CASO AUMENTO (Innesto / Mutazione) ---
            # # Usa il nome personalizzato dell'Aura (es. "Mutazione", "Impianto", "Tatuaggio")
            # prefisso_nome = aura_oggetto.nome_tipo_aumento or "Innesto"
            
            # # Logica Sottotipo:
            # # Se l'aura è soprannaturale o il nome suggerisce biologia -> MUTAZIONE
            # if aura_oggetto.is_soprannaturale or "Mutazione" in prefisso_nome:
            #     tipo_oggetto = 'POT'
            #     is_tecnologico = False
            # else:
            #     tipo_oggetto = 'INN'
            #     is_tecnologico = True # Gli innesti base sono tecnologici
            prefisso_nome = aura_oggetto.nome_tipo_aumento or "Innesto"
            tipo_oggetto = TIPO_OGGETTO_AUMENTO
            # Assegna lo slot solo se è un aumento
            slot_corpo_finale = infusione.slot_corpo_permessi

        else:
            # --- CASO POTENZIAMENTO (Mod / Materia) ---
            prefisso_nome = aura_oggetto.nome_tipo_potenziamento or "Materia"
            tipo_oggetto = TIPO_OGGETTO_POTENZIAMENTO
            # Logica Sottotipo:
        #     # Se l'aura spegne a 0 cariche -> È sicuramente tecnologico (MOD)
        #     if aura_oggetto.spegne_a_zero_cariche or "Mod" in prefisso_nome:
        #         tipo_oggetto = 'MOD'
        #         is_tecnologico = True
        #     else:
        #         tipo_oggetto = 'MAT' # Materia, Rune, Glifi
        #         is_tecnologico = False

        # # Override Tecnologico se l'aura lo impone
        # if aura_oggetto.spegne_a_zero_cariche:
        #     is_tecnologico = True
        
        if aura_oggetto.sigla == "ATE":
            is_tecnologico = True
        else:
            is_tecnologico == False
            
        # 3. Costruzione Nome
        nome_finale = nome_personalizzato or f"{prefisso_nome} di {infusione.nome}"

        # 4. Crea l'Oggetto
        nuovo_oggetto = Oggetto.objects.create(
            nome=nome_finale,
            testo=infusione.testo,
            tipo_oggetto=tipo_oggetto,
            infusione_generatrice=infusione,
            aura=aura_oggetto, 
            is_tecnologico=is_tecnologico,
            cariche_attuali=infusione.statistica_cariche.valore_base_predefinito if infusione.statistica_cariche else 0,
            slot_corpo=slot_corpo_finale
        )

        # 5. Copia le Statistiche Base
        for stat_inf in infusione.infusionestatisticabase_set.all():
            OggettoStatisticaBase.objects.create(
                oggetto=nuovo_oggetto,
                statistica=stat_inf.statistica,
                valore_base=stat_inf.valore_base
            )

        # 6. Copia Modificatori Manuali
        for stat_man in infusione.infusionestatistica_set.all():
            stat_obj = OggettoStatistica.objects.create(
                oggetto=nuovo_oggetto,
                statistica=stat_man.statistica,
                valore=stat_man.valore,
                tipo_modificatore=stat_man.tipo_modificatore,
                usa_limitazione_aura=stat_man.usa_limitazione_aura,
                usa_limitazione_elemento=stat_man.usa_limitazione_elemento,
                usa_condizione_text=stat_man.usa_condizione_text,
                condizione_text=stat_man.condizione_text
            )
            stat_obj.limit_a_aure.set(stat_man.limit_a_aure.all())
            stat_obj.limit_a_elementi.set(stat_man.limit_a_elementi.all())

        # 7. Copia Componenti & Conversione Mattoni (Logica esistente invariata)
        for comp in infusione.componenti.select_related('caratteristica').all():
            OggettoCaratteristica.objects.create(
                oggetto=nuovo_oggetto,
                caratteristica=comp.caratteristica,
                valore=comp.valore
            )
            
            mattone = Mattone.objects.filter(
                aura=infusione.aura_richiesta,
                caratteristica_associata=comp.caratteristica
            ).first()

            if mattone:
                for eff in mattone.mattonestatistica_set.all():
                    valore_totale = eff.valore * comp.valore
                    obj_stat, created = OggettoStatistica.objects.get_or_create(
                        oggetto=nuovo_oggetto,
                        statistica=eff.statistica,
                        defaults={
                            'valore': valore_totale,
                            'tipo_modificatore': eff.tipo_modificatore,
                            'usa_limitazione_aura': eff.usa_limitazione_aura,
                            'usa_limitazione_elemento': eff.usa_limitazione_elemento,
                            'usa_condizione_text': eff.usa_condizione_text,
                            'condizione_text': eff.condizione_text
                        }
                    )
                    if not created and obj_stat.tipo_modificatore == eff.tipo_modificatore:
                         obj_stat.valore += valore_totale
                         obj_stat.save()
                    elif created:
                        obj_stat.limit_a_aure.set(eff.limit_a_aure.all())
                        obj_stat.limit_a_elementi.set(eff.limit_a_elementi.all())
        
        # 8. Assegna al Personaggio
        nuovo_oggetto.sposta_in_inventario(proprietario)
        
        return nuovo_oggetto

    @staticmethod
    def installa_innesto(personaggio, innesto, slot):
        """
        Monta un Innesto/Mutazione su uno slot corporeo.
        """
        if innesto.tipo_oggetto not in [TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE]:
            raise ValidationError("Questo oggetto non è un innesto o mutazione.")
        
        occupante = Oggetto.objects.filter(
            tracciamento_inventario__inventario=personaggio,
            tracciamento_inventario__data_fine__isnull=True,
            slot_corpo=slot,
            is_equipaggiato=True
        ).first()
        
        if occupante:
            raise ValidationError(f"Lo slot {slot} è già occupato da {occupante.nome}.")
            
        innesto.slot_corpo = slot
        innesto.is_equipaggiato = True
        innesto.save()
        personaggio.aggiungi_log(f"Operazione riuscita: {innesto.nome} installato in {slot}.")
        return True

    @staticmethod
    def verifica_competenza_assemblaggio(personaggio: Personaggio, host: Oggetto, componente: Oggetto):
        """
        Verifica se il personaggio ha le skill e le statistiche per assemblare.
        Restituisce (Bool, Messaggio).
        """
        livello_oggetto = host.livello
        punteggi = personaggio.caratteristiche_base
        
        infusione = componente.infusione_generatrice
        if infusione:
            for comp_req in infusione.componenti.select_related('caratteristica').all():
                nome_stat = comp_req.caratteristica.nome
                val_richiesto = comp_req.valore
                val_posseduto = punteggi.get(nome_stat, 0)
                
                if val_posseduto < val_richiesto:
                    return False, f"Caratteristica insufficiente: {nome_stat} ({val_posseduto}/{val_richiesto})."

        # Verifica Abilità Specifica (Aura Tecnologica o Mondana)
        if host.is_tecnologico:
            abilita_necessaria = "Aura Tecnologica" 
            valore_abilita = personaggio.get_valore_statistica('ATEC')
            if valore_abilita == 0:
                 if personaggio.abilita_possedute.filter(nome__icontains=abilita_necessaria).exists():
                     valore_abilita = livello_oggetto 
        else:
            abilita_necessaria = "Aura Mondana - Assemblatore"
            valore_abilita = 0
            if personaggio.abilita_possedute.filter(nome__icontains=abilita_necessaria).exists():
                 valore_abilita = livello_oggetto 

        return True, "Competenza valida."

    @staticmethod
    def assembla_mod(assemblatore, oggetto_ospite, potenziamento, check_skills=True):
        """
        Gestisce l'installazione di Mod/Materia su un oggetto ospite.
        """
        proprietario_items = oggetto_ospite.inventario_corrente
        
        if not proprietario_items: raise ValidationError("Oggetto host non in inventario.")
        
        if not potenziamento.inventario_corrente: raise ValidationError("Il potenziamento non è in nessun inventario.")
        if potenziamento.inventario_corrente.id != proprietario_items.id:
             raise ValidationError("Host e Componente devono trovarsi nello stesso inventario.")

        if oggetto_ospite.pk == potenziamento.pk: raise ValidationError("Non puoi montare un oggetto su se stesso.")
        if potenziamento.ospitato_su: raise ValidationError("Il potenziamento è già montato altrove.")

        if check_skills:
            can_do, msg = GestioneOggettiService.verifica_competenza_assemblaggio(assemblatore, oggetto_ospite, potenziamento)
            if not can_do: raise ValidationError(msg)

        with transaction.atomic():
            potenziamento.sposta_in_inventario(None)
            potenziamento.ospitato_su = oggetto_ospite
            potenziamento.save()
            
            if hasattr(proprietario_items, 'personaggio'):
                msg = f"Installato {potenziamento.nome} su {oggetto_ospite.nome}."
                if assemblatore.id != proprietario_items.personaggio.id:
                    msg += f" (Eseguito da {assemblatore.nome})"
                proprietario_items.personaggio.aggiungi_log(msg)

    @staticmethod
    def rimuovi_mod(assemblatore, host, mod, check_skills=True):
        """
        Smonta un potenziamento.
        """
        proprietario_items = host.inventario_corrente
        if not proprietario_items: raise ValidationError("Oggetto host non in inventario.")
        
        if mod not in host.potenziamenti_installati.all(): raise ValidationError("Questo modulo non è installato sull'oggetto specificato.")

        if check_skills:
            can_do, msg = GestioneOggettiService.verifica_competenza_assemblaggio(assemblatore, host, mod)
            if not can_do: raise ValidationError(f"Non hai le competenze per smontare questo oggetto: {msg}")

        with transaction.atomic():
            host.potenziamenti_installati.remove(mod)
            mod.ospitato_su = None
            mod.sposta_in_inventario(proprietario_items) 
            mod.save()
            host.save()
            
            if hasattr(proprietario_items, 'personaggio'):
                msg = f"Smontato {mod.nome} da {host.nome}."
                if assemblatore.id != proprietario_items.personaggio.id:
                    msg += f" (Eseguito da {assemblatore.nome})"
                proprietario_items.personaggio.aggiungi_log(msg)
            
        return True

    @staticmethod
    def elabora_richiesta_assemblaggio(richiesta_id, esecutore):
        """
        Finalizza la richiesta.
        Gestisce pagamenti e operazioni fisiche sugli oggetti.
        """
        try: 
            req = RichiestaAssemblaggio.objects.select_related(
                'committente', 'artigiano', 'oggetto_host', 'componente', 'forgiatura_target'
            ).get(pk=richiesta_id)
        except RichiestaAssemblaggio.DoesNotExist: 
            raise ValidationError("Richiesta non trovata.")

        if req.stato != STATO_RICHIESTA_PENDENTE: 
            raise ValidationError("Richiesta già processata.")

        # --- LOGICA SPECIFICA PER TIPO ---

        if req.tipo_operazione == 'GRAF':
            # === CASO 3: INNESTO / MUTAZIONE ===
            # Mappatura DB Invertita per questo caso:
            # COMMITTENTE = Medico (Dottore)
            # ARTIGIANO   = Paziente (Chi riceve)
            
            # 1. Verifica Permessi: Deve accettare il Paziente (ARTIGIANO)
            if req.artigiano.proprietario != esecutore and not esecutore.is_staff:
                raise ValidationError("Solo il paziente (destinatario) può accettare questa operazione.")

            with transaction.atomic():
                # 2. Pagamento: Paziente paga Medico
                if req.offerta_crediti > 0:
                    if req.artigiano.crediti < req.offerta_crediti:
                        raise ValidationError("Il paziente non ha crediti sufficienti.")
                    req.artigiano.modifica_crediti(-req.offerta_crediti, f"Operazione da Dr. {req.committente.nome}")
                    req.committente.modifica_crediti(req.offerta_crediti, f"Paziente {req.artigiano.nome}")

                # 3. FIX CRITICO INTEGRITY ERROR
                # Salviamo l'ID della forgiatura perché stiamo per rompere il link
                if not req.forgiatura_target:
                    raise ValidationError("Forgiatura target non trovata.")
                
                forg_id = req.forgiatura_target.id
                
                # Sganciamo la forgiatura dalla richiesta PRIMA di processarla
                # Questo evita l'errore: "violates foreign key constraint"
                req.forgiatura_target = None
                req.save()

                # 4. Completamento Forgiatura
                # Il Medico (committente) è il creatore tecnico, quindi sblocca lui la forgiatura
                nuovo_obj = GestioneCraftingService.completa_forgiatura(
                    forg_id, 
                    req.committente 
                )
                
                # 5. Trasferimento al Paziente
                # Resettiamo eventuali stati di equipaggiamento automatico
                nuovo_obj.is_equipaggiato = False
                nuovo_obj.slot_corpo = None
                nuovo_obj.save()
                
                # Spostiamo l'oggetto nell'inventario del Paziente
                nuovo_obj.sposta_in_inventario(req.artigiano)

                # 6. Installazione sul Paziente
                GestioneOggettiService.installa_innesto(req.artigiano, nuovo_obj, req.slot_destinazione)

                # 7. Chiusura Richiesta
                req.stato = STATO_RICHIESTA_COMPLETATA
                req.save()
                
                # Log
                req.committente.aggiungi_log(f"Operazione completata su {req.artigiano.nome} ({nuovo_obj.nome}).")
                req.artigiano.aggiungi_log(f"Ricevuto innesto {nuovo_obj.nome} da Dr. {req.committente.nome}.")

        else:
            # === CASO 1 & 2: MONTAGGIO / FORGIATURA STANDARD ===
            # Mappatura DB Standard:
            # COMMITTENTE = Cliente (Chi chiede)
            # ARTIGIANO   = Lavoratore (Chi esegue)
            
            # 1. Verifica Permessi: Deve accettare il Lavoratore (ARTIGIANO)
            if req.artigiano.proprietario != esecutore and not esecutore.is_staff:
                raise ValidationError("Non sei l'artigiano designato per questo lavoro.")

            if req.tipo_operazione == TIPO_OPERAZIONE_FORGIATURA:
                if ForgiaturaInCorso.objects.filter(personaggio=req.artigiano).exists():
                     raise ValidationError("Hai già una forgiatura in corso.")

            with transaction.atomic():
                # 2. Pagamento: Cliente paga Lavoratore
                if req.offerta_crediti > 0:
                    if req.committente.crediti < req.offerta_crediti: 
                        raise ValidationError("Il committente non ha crediti sufficienti.")
                    req.committente.modifica_crediti(-req.offerta_crediti, f"Lavoro di {req.artigiano.nome}")
                    req.artigiano.modifica_crediti(req.offerta_crediti, f"Cliente {req.committente.nome}")

                # 3. Esecuzione Lavoro
                if req.tipo_operazione == TIPO_OPERAZIONE_FORGIATURA:
                    # L'Artigiano avvia la forgiatura per conto del Cliente
                    GestioneCraftingService.avvia_forgiatura(
                        personaggio=req.artigiano, 
                        infusione=req.infusione, 
                        destinatario_finale=req.committente,
                        is_academy=False,
                        aiutante=req.artigiano
                    )
                elif req.tipo_operazione == TIPO_OPERAZIONE_RIMOZIONE:
                    GestioneOggettiService.rimuovi_mod(req.artigiano, req.oggetto_host, req.componente)
                else:
                    GestioneOggettiService.assembla_mod(req.artigiano, req.oggetto_host, req.componente)
                
                # 4. Chiusura Richiesta
                req.stato = STATO_RICHIESTA_COMPLETATA
                req.save()
            
        return True

    @staticmethod
    def verifica_requisiti_supporto_innesto(personaggio, infusione):
        """
        Verifica se il personaggio può sostenere l'innesto/mutazione.
        Regole:
        1. Livello Aura PG >= Livello Infusione
        2. Caratteristiche PG >= Requisiti Componenti Infusione
        """
        # 1. Verifica Aura
        aura_req = infusione.aura_richiesta
        if aura_req:
            # Recupera il valore effettivo dell'aura sul personaggio
            valore_aura_pg = personaggio.get_valore_aura_effettivo(aura_req)
            # Il livello dell'infusione è la somma dei valori dei componenti
            livello_infusione = infusione.livello
            
            if valore_aura_pg < livello_infusione:
                return False

        # 2. Verifica Caratteristiche (Componenti)
        punteggi_pg = personaggio.caratteristiche_base
        # Cicla su tutti i componenti (caratteristiche richieste) dell'infusione
        for comp in infusione.componenti.select_related('caratteristica').all():
            nome_car = comp.caratteristica.nome
            val_richiesto = comp.valore
            val_posseduto = punteggi_pg.get(nome_car, 0)
            
            if val_posseduto < val_richiesto:
                return False
                
        return True

    @staticmethod
    def usa_carica_oggetto(oggetto):
        """
        Consuma una carica e avvia il timer se previsto.
        """
        if oggetto.cariche_attuali <= 0:
            raise ValidationError("Oggetto scarico.")
            
        with transaction.atomic():
            oggetto.cariche_attuali -= 1
            
            # Gestione Timer
            infusione = oggetto.infusione_generatrice
            attiva_timer = False
            if infusione and infusione.durata_attivazione > 0:
                durata = infusione.durata_attivazione
                oggetto.data_fine_attivazione = timezone.now() + timedelta(seconds=durata)
                attiva_timer = True
            
            oggetto.save()
            
        return {
            "cariche": oggetto.cariche_attuali, 
            "attivo_fino_a": oggetto.data_fine_attivazione,
            "has_timer": attiva_timer
        }
    
    @staticmethod
    def manipola_statistica_temporanea(personaggio, stat_sigla, operazione):
        """
        Operazione: 'consuma' (-1), 'reset' (torna al max).
        """
        # Trova la statistica e il suo valore MASSIMO attuale
        valore_max = personaggio.get_valore_statistica(stat_sigla)
        
        currents = personaggio.statistiche_temporanee or {}
        # Se non esiste nel JSON, parte dal massimo
        valore_attuale = currents.get(stat_sigla, valore_max)
        
        if operazione == 'consuma':
            if valore_attuale > 0:
                valore_attuale -= 1
        elif operazione == 'reset':
            valore_attuale = valore_max
            
        currents[stat_sigla] = valore_attuale
        personaggio.statistiche_temporanee = currents
        personaggio.save()
        
        return valore_attuale, valore_max
    

class GestioneCraftingService:

    @staticmethod
    def get_valore_statistica_aura(personaggio, aura, campo_configurazione):
        statistica_ref = getattr(aura, campo_configurazione, None)
        DEFAULT_COSTO = 100
        DEFAULT_TEMPO = 60
        if not statistica_ref:
            return DEFAULT_TEMPO if 'tempo' in campo_configurazione else DEFAULT_COSTO
        valore = personaggio.get_valore_statistica(statistica_ref.sigla) 
        return max(1, valore) if valore > 0 else statistica_ref.valore_base_predefinito

    @staticmethod
    def calcola_costi_forgiatura(personaggio, infusione):
        aura = infusione.aura_richiesta
        if not aura: return 0, 0
        costo_per_mattone = GestioneCraftingService.get_valore_statistica_aura(personaggio, aura, 'stat_costo_forgiatura')
        tempo_per_mattone = GestioneCraftingService.get_valore_statistica_aura(personaggio, aura, 'stat_tempo_forgiatura')
        livello = infusione.livello
        if livello == 0: livello = 1
        return livello * costo_per_mattone, livello * tempo_per_mattone

    @staticmethod
    def verifica_competenza_forgiatura(forgiatore, infusione, aiutante=None):
        """
        Verifica requisiti:
        1. INDISPENSABILE: Forgiatore deve avere Aura Primaria >= Livello Infusione.
        2. DELEGABILE: Aura Secondaria (se esiste) e Somma Caratteristiche.
        """
        livello = infusione.livello
        aura_primaria = infusione.aura_richiesta
        aura_secondaria = infusione.aura_infusione # Può essere None

        if not aura_primaria: return False, "Infusione non valida (manca aura richiesta)."

        # --- 1. REQUISITO INDISPENSABILE (Forgiatore) ---
        val_f_primaria = forgiatore.get_valore_aura_effettivo(aura_primaria)
        if val_f_primaria < livello:
            return False, f"Requisito Indispensabile mancante: {aura_primaria.nome} insufficiente ({val_f_primaria}/{livello})."

        # --- RACCOLTA REQUISITI DELEGABILI MANCANTI ---
        mancanze = []

        # Check Aura Secondaria (Delegabile)
        if aura_secondaria:
            val_f_secondaria = forgiatore.get_valore_aura_effettivo(aura_secondaria)
            if val_f_secondaria < livello:
                mancanze.append({'tipo': 'AURA', 'obj': aura_secondaria, 'val': livello, 'posseduto': val_f_secondaria})

        # Check Caratteristiche (Delegabili)
        # Recuperiamo i punteggi base del forgiatore
        stats_forgiatore = forgiatore.caratteristiche_base
        for comp in infusione.componenti.select_related('caratteristica').all():
            nome_stat = comp.caratteristica.nome
            val_richiesto = comp.valore
            val_posseduto = stats_forgiatore.get(nome_stat, 0)
            
            if val_posseduto < val_richiesto:
                diff = val_richiesto - val_posseduto
                mancanze.append({'tipo': 'STAT', 'obj': comp.caratteristica, 'val': val_richiesto, 'manca': diff})

        # Se non ci sono mancanze, il forgiatore è autosufficiente
        if not mancanze:
            return True, "Autosufficiente"

        # --- SE SERVONO AIUTI ---
        if not aiutante:
            return False, "Requisiti delegabili mancanti (Serve Aiuto o Accademia)."

        # Verifica se l'Aiutante può coprire le mancanze
        # Regola Aiutante: Deve avere Aura Primaria OR Aura Secondaria (se esiste) >= Livello
        val_a_primaria = aiutante.get_valore_aura_effettivo(aura_primaria)
        val_a_secondaria = aiutante.get_valore_aura_effettivo(aura_secondaria) if aura_secondaria else 0
        
        ha_competenza_base_aiutante = (val_a_primaria >= livello) or (val_a_secondaria >= livello)
        
        if not ha_competenza_base_aiutante:
            return False, f"L'aiutante non ha la competenza d'aura minima richiesta ({aura_primaria.nome} o {aura_secondaria.nome if aura_secondaria else ''})."

        # Verifica se l'Aiutante copre le specifiche mancanze (Stats o Aura Secondaria)
        stats_aiutante = aiutante.caratteristiche_base
        
        for m in mancanze:
            if m['tipo'] == 'AURA':
                # Se mancava l'aura secondaria al forgiatore, l'aiutante ce l'ha?
                if val_a_secondaria < livello:
                    return False, f"Neanche l'aiutante soddisfa l'Aura Secondaria {m['obj'].nome}."
            elif m['tipo'] == 'STAT':
                # Logica Cooperativa: Sommiamo le stats? O l'aiutante deve avere il valore pieno?
                # Solitamente nella forgiatura cooperativa si usa il valore più alto o si somma.
                # Qui assumiamo che l'aiutante debba coprire il "buco" o avere il requisito.
                # Interpretazione: "Unite a quelle del personaggio". Somma dei valori.
                val_a_stat = stats_aiutante.get(m['obj'].nome, 0)
                totale = (m['val'] - m['manca']) + val_a_stat # (Quello che ha il forgiatore) + Aiutante
                if totale < m['val']:
                     return False, f"Statistica {m['obj'].nome} insufficiente anche combinata ({totale}/{m['val']})."

        return True, "Requisiti soddisfatti con aiuto."

    @staticmethod
    def avvia_forgiatura(personaggio, infusione, slot_target=None, destinatario_finale=None, is_academy=False, aiutante=None):
        # Calcolo costi base (Materiali)
        costo_materiali, durata_secondi = GestioneCraftingService.calcola_costi_tempi(personaggio, infusione)
        
        costo_totale = 0
        descrizione = ""
        
        # --- LOGICA ACCADEMIA ---
        if is_academy:
            # Requisito Indispensabile deve essere comunque rispettato dal PG? 
            # Solitamente l'Accademia fa tutto, ma se vuoi mantenere la regola "Aura Primaria Indispensabile" anche per Accademia, decommenta le righe sotto.
            # can, msg = GestioneCraftingService.verifica_competenza_forgiatura(personaggio, infusione) # Check base
            # if "Indispensabile" in msg and not can: raise ValidationError(msg)

            # Costo Accademia = Costo Materiali + (Livello * Costo Unitario Aura)
            # Ovvero paga "doppio" il costo dei mattoni (uno per materiali, uno per il servizio)
            # Nota: calcola_costi_tempi restituisce già (Livello * Costo_Unitario).
            costo_servizio = costo_materiali 
            costo_totale = costo_materiali + costo_servizio
            descrizione = f"Accademia (Materiali + Servizio): {infusione.nome}"
            
        else:
            # --- LOGICA FAI DA TE / AIUTO ---
            forgiatore = destinatario_finale if destinatario_finale else personaggio
            helper = aiutante
            
            # Verifica Requisiti Completa
            can, msg = GestioneCraftingService.verifica_competenza_forgiatura(forgiatore, infusione, aiutante=helper)
            if not can: 
                raise ValidationError(msg)

            costo_totale = costo_materiali
            descrizione = f"Materiali Forgiatura: {infusione.nome}"

        # Verifica Crediti
        if personaggio.crediti < costo_totale:
            raise ValidationError(f"Crediti insufficienti. Richiesti: {costo_totale}")

        # Gestione Coda (identica a prima)
        now = timezone.now()
        ultima_forgiatura = ForgiaturaInCorso.objects.filter(personaggio=personaggio).order_by('-data_fine_prevista').first()
        data_inizio_lavoro = now
        if ultima_forgiatura and ultima_forgiatura.data_fine_prevista > now:
            data_inizio_lavoro = ultima_forgiatura.data_fine_prevista
        
        fine_prevista = data_inizio_lavoro + timedelta(seconds=durata_secondi)

        with transaction.atomic():
            personaggio.modifica_crediti(-costo_totale, descrizione)
            forgiatura = ForgiaturaInCorso.objects.create(
                personaggio=personaggio, 
                infusione=infusione, 
                data_inizio=data_inizio_lavoro,
                data_fine_prevista=fine_prevista, 
                slot_target=slot_target,
                destinatario_finale=destinatario_finale
            )
            
        return forgiatura

    @staticmethod
    def completa_forgiatura(forgiatura_id, attore, slot_scelto=None, destinatario_diretto=None):
        """
        Completa forgiatura.
        - destinatario_diretto: Se specificato, forza il proprietario (es. installazione diretta su alt).
        """
        try:
            task = ForgiaturaInCorso.objects.get(pk=forgiatura_id)
        except ForgiaturaInCorso.DoesNotExist:
            raise ValidationError("Forgiatura non trovata.")
            
        is_creator = task.personaggio.id == attore.id
        is_recipient = task.destinatario_finale and task.destinatario_finale.id == attore.id

        if not is_creator and not is_recipient:
             raise ValidationError("Non autorizzato a ritirare questo oggetto.")
            
        if not task.is_pronta: raise ValidationError("Non ancora completata.")
        
        with transaction.atomic():
            # DETERMINA PROPRIETARIO:
            # 1. Destinatario forzato (Installazione diretta su Alt)
            # 2. Destinatario finale (Forgiatura conto terzi pre-impostata)
            # 3. Forgiatore (Default)
            proprietario = destinatario_diretto if destinatario_diretto else (
                task.destinatario_finale if task.destinatario_finale else task.personaggio
            )
            
            # Crea l'oggetto direttamente nell'inventario del proprietario corretto
            nuovo_oggetto = GestioneOggettiService.crea_oggetto_da_infusione(task.infusione, proprietario)
            
            # Installazione Immediata (Innesto)
            if slot_scelto:
                # Poiché crea_oggetto_da_infusione ha già assegnato l'oggetto a 'proprietario',
                # possiamo installarlo direttamente su di lui.
                GestioneOggettiService.installa_innesto(proprietario, nuovo_oggetto, slot_scelto)
            
            elif task.slot_target and proprietario.id == task.personaggio.id:
                # Legacy auto-equip (solo su se stessi)
                nuovo_oggetto.slot_corpo = task.slot_target
                nuovo_oggetto.is_equipaggiato = True
                nuovo_oggetto.save()
            
            task.delete()
            
            # Log
            if proprietario.id != attore.id:
                attore.aggiungi_log(f"Forgiato e installato {nuovo_oggetto.nome} su {proprietario.nome}")
                proprietario.aggiungi_log(f"Ricevuto innesto {nuovo_oggetto.nome} da {attore.nome}")
            else:
                attore.aggiungi_log(f"Forgiatura completata: {nuovo_oggetto.nome}")
            
        return nuovo_oggetto

    @staticmethod
    def acquista_da_negozio(personaggio, oggetto_base_id):
        try:
            template = OggettoBase.objects.get(pk=oggetto_base_id)
        except OggettoBase.DoesNotExist:
            raise ValidationError("Oggetto non trovato nel listino.")
            
        if not template.in_vendita:
            raise ValidationError("Questo oggetto non è più in vendita.")
            
        costo = template.costo
        if personaggio.crediti < costo:
            raise ValidationError(f"Crediti insufficienti. Costo: {costo}")
            
        with transaction.atomic():
            personaggio.modifica_crediti(-costo, f"Acquisto negozio: {template.nome}")
            
            nuovo_oggetto = Oggetto.objects.create(
                nome=template.nome,
                testo=template.descrizione,
                tipo_oggetto=template.tipo_oggetto,
                classe_oggetto=template.classe_oggetto,
                is_tecnologico=template.is_tecnologico,
                costo_acquisto=costo,
                attacco_base=template.attacco_base,
                oggetto_base_generatore=template,
                in_vendita=False,
                is_equipaggiato=False,
                cariche_attuali=0
            )
            for stat_link in template.oggettobasestatisticabase_set.all():
                OggettoStatisticaBase.objects.create(
                    oggetto=nuovo_oggetto,
                    statistica=stat_link.statistica,
                    valore_base=stat_link.valore_base
                )
            for mod_link in template.oggettobasemodificatore_set.all():
                OggettoStatistica.objects.create(
                    oggetto=nuovo_oggetto,
                    statistica=mod_link.statistica,
                    valore=mod_link.valore,
                    tipo_modificatore=mod_link.tipo_modificatore
                )
            
            nuovo_oggetto.sposta_in_inventario(personaggio)
            
        return nuovo_oggetto

    @staticmethod
    def calcola_costi_tempi(personaggio, infusione):
        """Restituisce (Costo Crediti, Durata Secondi)."""
        aura = infusione.aura_richiesta
        if not aura: return 0, 0
        
        c_unit = GestioneCraftingService.get_valore_statistica_aura(personaggio, aura, 'stat_costo_forgiatura')
        t_unit = GestioneCraftingService.get_valore_statistica_aura(personaggio, aura, 'stat_tempo_forgiatura')
        
        lvl = max(1, infusione.livello)
        return lvl * c_unit, lvl * t_unit

    
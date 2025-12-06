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
    TIPO_OPERAZIONE_FORGIATURA, TIPO_OPERAZIONE_RIMOZIONE,
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
    def crea_oggetto_da_infusione(infusione, proprietario, nome_pers=None):
        """Factory pura: crea record DB."""
        tipo = TIPO_OGGETTO_FISICO
        if infusione.aura_richiesta:
             nome_a = infusione.aura_richiesta.nome.lower()
             if "tecnologic" in nome_a: tipo = TIPO_OGGETTO_MOD
             elif "mondan" in nome_a: tipo = TIPO_OGGETTO_MATERIA
        
        obj = Oggetto.objects.create(
            nome=nome_pers or infusione.nome, 
            tipo_oggetto=tipo, 
            infusione_generatrice=infusione,
            is_tecnologico=(tipo in [TIPO_OGGETTO_MOD, TIPO_OGGETTO_INNESTO]),
            proprietario=proprietario
        )
        # Copia statistiche e caratteristiche...
        for s in infusione.infusionestatisticabase_set.all():
            OggettoStatisticaBase.objects.create(oggetto=obj, statistica=s.statistica, valore_base=s.valore_base)
        for c in infusione.componenti.all():
            OggettoCaratteristica.objects.create(oggetto=obj, caratteristica=c.caratteristica, valore=c.valore)
            
        obj.sposta_in_inventario(proprietario)
        return obj


    @staticmethod
    def verifica_competenza_assemblaggio(personaggio: Personaggio, host: Oggetto, componente: Oggetto):
        """
        Verifica se il personaggio ha le skill e le statistiche per assemblare.
        Restituisce (Bool, Messaggio).
        """
        livello_oggetto = host.livello
        punteggi = personaggio.caratteristiche_base
        
        # 1. Verifica Caratteristiche Base necessarie per il componente
        # (Basato sui mattoni dell'infusione generatrice del componente)
        infusione = componente.infusione_generatrice
        if infusione:
            for comp_req in infusione.componenti.select_related('caratteristica').all():
                nome_stat = comp_req.caratteristica.nome
                val_richiesto = comp_req.valore
                val_posseduto = punteggi.get(nome_stat, 0)
                
                if val_posseduto < val_richiesto:
                    return False, f"Caratteristica insufficiente: {nome_stat} ({val_posseduto}/{val_richiesto})."

        # 2. Verifica Abilità Specifica (Aura Tecnologica o Mondana)
        if host.is_tecnologico:
            abilita_necessaria = "Aura Tecnologica" # O codice 'ATEC'
            # Esempio: recupera da Punteggi o Abilità
            valore_abilita = personaggio.get_valore_statistica('ATEC')
            # Fallback se non è una statistica mappata
            if valore_abilita == 0:
                 if personaggio.abilita_possedute.filter(nome__icontains=abilita_necessaria).exists():
                     valore_abilita = livello_oggetto # Passa d'ufficio se ha l'abilità
        else:
            abilita_necessaria = "Aura Mondana - Assemblatore"
            valore_abilita = 0
            if personaggio.abilita_possedute.filter(nome__icontains=abilita_necessaria).exists():
                 # Usiamo una caratteristica base come proxy del valore (es. Destrezza o Intelligenza)
                 # O semplicemente check booleano. Qui assumiamo booleano OK.
                 valore_abilita = livello_oggetto 

        if valore_abilita < livello_oggetto:
             # Nota: Se vuoi essere rigido scommenta la riga sotto
             # return False, f"Livello competenza insufficiente ({valore_abilita}) per oggetto Lv.{livello_oggetto}."
             pass 

        return True, "Competenza valida."


    @staticmethod
    def equipaggia_oggetto(personaggio: Personaggio, oggetto: Oggetto):
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
    
# Inserire dentro class GestioneOggettiService:

    @staticmethod
    def assembla_mod(assemblatore, oggetto_host, potenziamento, check_skills=True):
        """
        Gestisce l'installazione di Mod/Materia.
        Supporta l'esecuzione da parte di terzi (Artigiani/Admin).
        """
        # 1. Controlli Coerenza Inventario
        proprietario_items = oggetto_host.inventario_corrente
        if not proprietario_items:
             raise ValidationError("Oggetto host non in inventario.")
        
        # Verifica che Host e Componente siano nello STESSO inventario
        # (Indipendentemente da chi sta eseguendo l'azione)
        if not potenziamento.inventario_corrente:
             raise ValidationError("Il potenziamento non è in nessun inventario.")

        if potenziamento.inventario_corrente.id != proprietario_items.id:
             raise ValidationError("Host e Componente devono trovarsi nello stesso inventario per essere assemblati.")

        if oggetto_host.pk == potenziamento.pk:
            raise ValidationError("Non puoi montare un oggetto su se stesso.")
        if potenziamento.ospitato_su:
            raise ValidationError("Il potenziamento è già montato altrove.")

        # 2. Check Skills (dell'assemblatore)
        if check_skills:
            can_do, msg = GestioneOggettiService.verifica_competenza_assemblaggio(assemblatore, oggetto_host, potenziamento)
            if not can_do:
                raise ValidationError(msg)

        # 3. Logica Materia/Mod (Check Compatibilità)
        classe = oggetto_host.classe_oggetto
        
        if potenziamento.tipo_oggetto == TIPO_OGGETTO_MATERIA: # 'MAT'
            if oggetto_host.is_tecnologico:
                 raise ValidationError("Le Materie non possono essere montate su oggetti Tecnologici.")
            if oggetto_host.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MATERIA).exists():
                raise ValidationError("È già presente una Materia.")
            if oggetto_host.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD).exists():
                raise ValidationError("Impossibile installare Materia: presenti Mod.")
            
            if classe:
                caratts_item = set(potenziamento.caratteristiche.values_list('id', flat=True))
                if not caratts_item and potenziamento.infusione_generatrice:
                     caratts_item = set(potenziamento.infusione_generatrice.componenti.values_list('caratteristica__id', flat=True))
                permessi_ids = set(classe.mattoni_materia_permessi.values_list('id', flat=True))
                
                if not caratts_item.issubset(permessi_ids):
                     diff = caratts_item - permessi_ids
                     raise ValidationError(f"Materia incompatibile con la classe dell'oggetto (ID invalidi: {diff}).")

        elif potenziamento.tipo_oggetto == TIPO_OGGETTO_MOD: # 'MOD'
            if not oggetto_host.is_tecnologico:
                raise ValidationError("Le Mod richiedono un oggetto Tecnologico.")
            if oggetto_host.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MATERIA).exists():
                raise ValidationError("Impossibile installare Mod: presente Materia.")
            if not classe:
                raise ValidationError("Oggetto privo di Classe, impossibile montare Mod.")

            count_mods = oggetto_host.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD).count()
            if count_mods >= classe.max_mod_totali:
                raise ValidationError(f"Slot Mod esauriti (Max {classe.max_mod_totali}).")
            
            # (Qui ometti i controlli specifici per caratteristica se vuoi semplificare, 
            #  altrimenti reinserisci il ciclo 'for c_id in caratts_new' dal codice precedente)

        else:
             raise ValidationError(f"Tipo oggetto '{potenziamento.tipo_oggetto}' non supportato.")

        # 4. Esecuzione
        with transaction.atomic():
            potenziamento.sposta_in_inventario(None)
            potenziamento.ospitato_su = oggetto_host
            potenziamento.save()
            
            # Log
            if hasattr(proprietario_items, 'personaggio'):
                msg = f"Installato {potenziamento.nome} su {oggetto_host.nome}."
                if assemblatore.id != proprietario_items.personaggio.id:
                    msg += f" (Eseguito da {assemblatore.nome})"
                proprietario_items.personaggio.aggiungi_log(msg)

    @staticmethod
    def rimuovi_mod(assemblatore, host, mod, check_skills=True):
        """
        Smonta un potenziamento.
        """
        # 1. Controlli Coerenza
        proprietario_items = host.inventario_corrente
        if not proprietario_items:
             raise ValidationError("Oggetto host non in inventario.")
        
        if mod not in host.potenziamenti_installati.all():
            raise ValidationError("Questo modulo non è installato sull'oggetto specificato.")

        # 2. Check Skills (dell'assemblatore)
        if check_skills:
            can_do, msg = GestioneOggettiService.verifica_competenza_assemblaggio(assemblatore, host, mod)
            if not can_do:
                raise ValidationError(f"Competenze insufficienti per smontare: {msg}")

        # 3. Esecuzione
        with transaction.atomic():
            host.potenziamenti_installati.remove(mod)
            mod.ospitato_su = None
            
            # IMPORTANTE: Restituisci l'oggetto al PROPRIETARIO DELL'HOST
            mod.sposta_in_inventario(proprietario_items) 
            mod.save()
            
            # Ricalcolo stats rimosso perché non presente in questo snapshot
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
        Gestisce l'accettazione del lavoro.
        """
        try: req = RichiestaAssemblaggio.objects.get(pk=richiesta_id)
        except: raise ValidationError("Richiesta non trovata.")

        if req.artigiano.proprietario != esecutore and not (esecutore.is_staff):
             raise ValidationError("Non autorizzato.")
        if req.stato != STATO_RICHIESTA_PENDENTE: raise ValidationError("Già processata.")

        with transaction.atomic():
            # 1. Pagamento Offerta (Committente -> Artigiano)
            if req.offerta_crediti > 0:
                if req.committente.crediti < req.offerta_crediti: raise ValidationError("Committente senza fondi.")
                req.committente.modifica_crediti(-req.offerta_crediti, f"Pagamento a {req.artigiano.nome}")
                req.artigiano.modifica_crediti(req.offerta_crediti, f"Lavoro da {req.committente.nome}")

            # 2. Dispatcher
            if req.tipo_operazione == TIPO_OPERAZIONE_FORGIATURA:
                # L'artigiano avvia il timer. Paga i MATERIALI.
                # L'oggetto andrà al committente alla fine.
                GestioneCraftingService.avvia_forgiatura(
                    personaggio=req.artigiano, 
                    infusione=req.infusione, 
                    destinatario_finale=req.committente,
                    is_academy=False,
                    aiutante=req.artigiano # Passiamo esplicitamente l'artigiano come aiutante
                )
                req.artigiano.aggiungi_log(f"Ha iniziato a forgiare {req.infusione.nome} per {req.committente.nome}.")
                
            elif req.tipo_operazione == TIPO_OPERAZIONE_RIMOZIONE:
                # Immediato
                from .services import GestioneOggettiService # Import locale
                GestioneOggettiService.rimuovi_mod(req.artigiano, req.oggetto_host, req.componente)
                
            else: # Installazione
                # Immediato
                from .services import GestioneOggettiService
                GestioneOggettiService.assembla_mod(req.artigiano, req.oggetto_host, req.componente)

            req.stato = STATO_RICHIESTA_COMPLETATA
            req.save()

        return True    




class GestioneCraftingService:
    """
    Gestisce i processi temporali e i costi di forgiatura.
    Si appoggia a GestioneOggettiService per la creazione fisica degli item.
    """


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
        Verifica i requisiti per la forgiatura, eventualmente con un aiutante.
        
        REGOLE:
        1. Forgiatore: DEVE avere Aura Richiesta >= Livello.
        2. Aiutante (se c'è): DEVE avere Aura Richiesta O Aura Infusione >= Livello.
        3. Combinata: Aura Infusione (se c'è) e Caratteristiche devono essere soddisfatte 
           da ALMENO UNO dei due.
        """
        livello = infusione.livello
        
        # --- 1. CHECK AURA PRINCIPALE (Vincolo Forgiatore) ---
        if not infusione.aura_richiesta:
            return False, "Infusione non valida (manca Aura Richiesta)."
            
        val_aura_main_forgiatore = forgiatore.get_valore_aura_effettivo(infusione.aura_richiesta)
        if val_aura_main_forgiatore < livello:
            return False, f"Il Forgiatore non ha l'Aura richiesta ({infusione.aura_richiesta.nome}) al livello necessario ({val_aura_main_forgiatore}/{livello})."

        # --- 2. CHECK AIUTANTE (Vincolo di partecipazione) ---
        if aiutante:
            val_aura_main_aiutante = aiutante.get_valore_aura_effettivo(infusione.aura_richiesta)
            has_valid_main = val_aura_main_aiutante >= livello
            
            has_valid_sec = False
            if infusione.aura_infusione:
                val_aura_sec_aiutante = aiutante.get_valore_aura_effettivo(infusione.aura_infusione)
                has_valid_sec = val_aura_sec_aiutante >= livello
            
            if not (has_valid_main or has_valid_sec):
                return False, "L'Aiutante non possiede né l'Aura Richiesta né l'Aura Infusione al livello corretto."

        # --- 3. CHECK AURA SECONDARIA (Combinata) ---
        if infusione.aura_infusione:
            val_f = forgiatore.get_valore_aura_effettivo(infusione.aura_infusione)
            val_a = aiutante.get_valore_aura_effettivo(infusione.aura_infusione) if aiutante else 0
            
            if max(val_f, val_a) < livello:
                return False, f"Livello Aura Infusione insufficiente ({infusione.aura_infusione.nome}). Max posseduto: {max(val_f, val_a)}/{livello}."

        # --- 4. CHECK CARATTERISTICHE (Combinata) ---
        stats_f = forgiatore.caratteristiche_base
        stats_a = aiutante.caratteristiche_base if aiutante else {}
        
        for comp in infusione.componenti.select_related('caratteristica').all():
            nome = comp.caratteristica.nome
            req = comp.valore
            
            val_f = stats_f.get(nome, 0)
            val_a = stats_a.get(nome, 0)
            
            if max(val_f, val_a) < req:
                return False, f"Caratteristica {nome} insufficiente. Max posseduto: {max(val_f, val_a)}/{req}."

        return True, "Requisiti soddisfatti."

    @staticmethod
    def get_valore_statistica_aura(personaggio, aura, campo):
        stat = getattr(aura, campo, None)
        default = 60 if 'tempo' in campo else 100
        if not stat: return default
        val = personaggio.get_valore_statistica(stat.sigla)
        return max(1, val) if val > 0 else stat.valore_base_predefinito

    @staticmethod
    def calcola_costi_tempi(personaggio, infusione):
        """Restituisce (Costo Materiali, Durata Secondi)"""
        aura = infusione.aura_richiesta
        if not aura: return 0, 0
        c_unit = GestioneCraftingService.get_valore_statistica_aura(personaggio, aura, 'stat_costo_forgiatura')
        t_unit = GestioneCraftingService.get_valore_statistica_aura(personaggio, aura, 'stat_tempo_forgiatura')
        lvl = max(1, infusione.livello)
        return lvl * c_unit, lvl * t_unit

    @staticmethod
    def avvia_forgiatura(personaggio, infusione, slot_target=None, destinatario_finale=None, is_academy=False):
        """
        Avvia il timer di crafting.
        - is_academy=True: Ignora skill, Costo fisso 200, Timer parte comunque.
        - is_academy=False: Check skill, Costo materiali, Timer parte.
        """
        
        # LOGICA COSTI E REQUISITI
        costo_da_pagare = 0
        descrizione_pagamento = ""
        
        if is_academy:
            costo_da_pagare = 200 # Costo fisso Accademia
            descrizione_pagamento = f"Forgiatura Accademia: {infusione.nome}"
            # Accademia ignora i requisiti di competenza del PG
        else:
            forgiatore = destinatario_finale if destinatario_finale else personaggio
            helper = personaggio if destinatario_finale else None # Se faccio da solo, helper è None
            # Verifica competenze (se non è accademia)
            can_do, msg = GestioneCraftingService.verifica_competenza_forgiatura(personaggio, infusione, aiutante=helper)
            if not can_do: raise ValidationError(msg)
            
            # Calcolo costi materiali
            costo_mat, _ = GestioneCraftingService.calcola_costi_tempi(personaggio, infusione)
            costo_da_pagare = costo_mat
            descrizione_pagamento = f"Materiali forgiatura: {infusione.nome}"

        # Verifica fondi
        if personaggio.crediti < costo_da_pagare:
            raise ValidationError(f"Crediti insufficienti. Servono {costo_da_pagare} CR.")
            
        # Calcolo Tempi (Vale per tutti, anche Accademia)
        _, durata = GestioneCraftingService.calcola_costi_tempi(personaggio, infusione)
        fine = timezone.now() + timedelta(seconds=durata)

        with transaction.atomic():
            personaggio.modifica_crediti(-costo_da_pagare, descrizione_pagamento)
            
            ForgiaturaInCorso.objects.create(
                personaggio=personaggio,
                infusione=infusione,
                data_fine_prevista=fine,
                slot_target=slot_target,
                destinatario_finale=destinatario_finale
            )
            
        return True

    @staticmethod
    def completa_forgiatura(task_id, attore):
        try:
            task = ForgiaturaInCorso.objects.get(pk=task_id, personaggio=attore)
        except ForgiaturaInCorso.DoesNotExist:
            raise ValidationError("Task non trovato.")
        
        if not task.is_pronta: raise ValidationError("Non ancora completata.")
        
        with transaction.atomic():
            # Determina chi riceve l'oggetto
            proprietario = task.destinatario_finale if task.destinatario_finale else attore
            
            # Crea Fisicamente (Factory in GestioneOggetti)
            nuovo_obj = GestioneOggettiService.crea_oggetto_da_infusione(task.infusione, proprietario)
            
            task.delete()
            
            if task.destinatario_finale:
                attore.aggiungi_log(f"Lavoro terminato: {nuovo_obj.nome} inviato a {task.destinatario_finale.nome}.")
                task.destinatario_finale.aggiungi_log(f"Consegna ricevuta: {nuovo_obj.nome} da {attore.nome}.")
            else:
                attore.aggiungi_log(f"Forgiatura completata: {nuovo_obj.nome}.")
                
        return nuovo_obj

    

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
            
            # Creazione manuale perché da Template è diverso che da Infusione
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
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
    TIPO_OPERAZIONE_FORGIATURA, TIPO_OPERAZIONE_RIMOZIONE, TIPO_OPERAZIONE_INNESTO,
)

class GestioneOggettiService:
    """
    Gestisce la manipolazione fisica degli oggetti: creazione, assemblaggio, smontaggio.
    """

    @staticmethod
    def crea_oggetto_da_infusione(infusione, proprietario, nome_pers=None):
        tipo = TIPO_OGGETTO_FISICO
        if infusione.aura_richiesta:
             nome_a = infusione.aura_richiesta.nome.lower()
             if "tecnologic" in nome_a: tipo = TIPO_OGGETTO_MOD
             elif "mondan" in nome_a: tipo = TIPO_OGGETTO_MATERIA
        
        # NOTA: Rimosso proprietario=proprietario per evitare TypeError
        obj = Oggetto.objects.create(
            nome=nome_pers or infusione.nome, 
            tipo_oggetto=tipo, 
            infusione_generatrice=infusione,
            is_tecnologico=(tipo in [TIPO_OGGETTO_MOD, TIPO_OGGETTO_INNESTO]),
            cariche_attuali=infusione.statistica_cariche.valore_predefinito if infusione.statistica_cariche else 0
        )

        for s in infusione.infusionestatisticabase_set.all():
            OggettoStatisticaBase.objects.create(oggetto=obj, statistica=s.statistica, valore_base=s.valore_base)
        for c in infusione.componenti.all():
            OggettoCaratteristica.objects.create(oggetto=obj, caratteristica=c.caratteristica, valore=c.valore)
            
        obj.sposta_in_inventario(proprietario)
        return obj

    @staticmethod
    def verifica_competenza_assemblaggio(personaggio, host, componente):
        punteggi = personaggio.caratteristiche_base
        if componente.infusione_generatrice:
            for comp_req in componente.infusione_generatrice.componenti.select_related('caratteristica').all():
                val_posseduto = punteggi.get(comp_req.caratteristica.nome, 0)
                if val_posseduto < comp_req.valore:
                    return False, f"Caratteristica insufficiente: {comp_req.caratteristica.nome}"
        return True, "Competenza valida."

    @staticmethod
    def verifica_competenza_assemblaggio(personaggio, host, componente):
        """Check per Installazione/Rimozione (Resta invariato: serve un solo operatore)."""
        punteggi = personaggio.caratteristiche_base
        if componente.infusione_generatrice:
            for comp_req in componente.infusione_generatrice.componenti.select_related('caratteristica').all():
                val_posseduto = punteggi.get(comp_req.caratteristica.nome, 0)
                if val_posseduto < comp_req.valore:
                    return False, f"Caratteristica insufficiente: {comp_req.caratteristica.nome}"
        return True, "Competenza valida."

    @staticmethod
    def assembla_mod(assemblatore, oggetto_host, potenziamento, check_skills=True):
        proprietario_items = oggetto_host.inventario_corrente
        if not proprietario_items: raise ValidationError("Oggetto host non in inventario.")
        
        if not potenziamento.inventario_corrente: raise ValidationError("Potenziamento disperso.")
        if potenziamento.inventario_corrente.id != proprietario_items.id:
             raise ValidationError("Host e Componente devono trovarsi nello stesso inventario.")

        if oggetto_host.pk == potenziamento.pk: raise ValidationError("Loop rilevato.")
        if potenziamento.ospitato_su: raise ValidationError("Già montato.")

        if check_skills:
            can_do, msg = GestioneOggettiService.verifica_competenza_assemblaggio(assemblatore, oggetto_host, potenziamento)
            if not can_do: raise ValidationError(msg)
        
        # Logica Mod/Materia semplificata per brevità (assumiamo i check del tipo qui)
        if potenziamento.tipo_oggetto == 'MAT' and oggetto_host.is_tecnologico:
             raise ValidationError("Materia su Tecno non ammessa.")

        with transaction.atomic():
            potenziamento.sposta_in_inventario(None)
            potenziamento.ospitato_su = oggetto_host
            potenziamento.save()
            if hasattr(proprietario_items, 'personaggio'):
                msg = f"Installato {potenziamento.nome} su {oggetto_host.nome}."
                if assemblatore.id != proprietario_items.personaggio.id:
                    msg += f" (Eseguito da {assemblatore.nome})"
                proprietario_items.personaggio.aggiungi_log(msg)

    @staticmethod
    def rimuovi_mod(assemblatore, host, mod, check_skills=True):
        proprietario_items = host.inventario_corrente
        if not proprietario_items: raise ValidationError("Oggetto host non in inventario.")
        if mod not in host.potenziamenti_installati.all(): raise ValidationError("Modulo non installato.")

        if check_skills:
            can_do, msg = GestioneOggettiService.verifica_competenza_assemblaggio(assemblatore, host, mod)
            if not can_do: raise ValidationError(f"Competenze insufficienti: {msg}")

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
    def verifica_requisiti_supporto_innesto(personaggio, infusione):
        """
        Verifica se il personaggio ha i requisiti fisici/aurici per 'indossare' l'innesto/mutazione.
        Regole:
        1. Caratteristiche (Componenti) >= Valore Richiesto
        2. Aura Relativa (quella dell'infusione) >= Livello Totale Oggetto
        """
        if not infusione: return True
        
        # 1. Check Livello Aura (Tecnologica o Innata)
        # L'aura richiesta dall'oggetto deve essere posseduta dal ricevente a un livello sufficiente
        aura_req = infusione.aura_richiesta
        if aura_req:
            livello_oggetto = infusione.livello
            valore_aura_pg = personaggio.get_valore_aura_effettivo(aura_req)
            if valore_aura_pg < livello_oggetto:
                return False
        
        # 2. Check Caratteristiche (Componenti)
        punteggi_pg = personaggio.caratteristiche_base
        for comp in infusione.componenti.select_related('caratteristica').all():
            nome_stat = comp.caratteristica.nome
            val_richiesto = comp.valore
            val_posseduto = punteggi_pg.get(nome_stat, 0)
            
            if val_posseduto < val_richiesto:
                return False

        return True


    @staticmethod
    def installa_innesto(personaggio, innesto, slot):
        """
        Monta un Innesto/Mutazione su uno slot corporeo.
        Include verifica requisiti ricevente.
        """
        # 1. Verifica Tipo
        if innesto.tipo_oggetto not in [TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE]:
            raise ValidationError("Questo oggetto non può essere innestato nel corpo.")
            
        # 2. Verifica Requisiti Ricevente (NUOVO)
        if innesto.infusione_generatrice:
            is_compatibile = GestioneOggettiService.verifica_requisiti_supporto_innesto(personaggio, innesto.infusione_generatrice)
            if not is_compatibile:
                raise ValidationError(f"{personaggio.nome} non ha i requisiti (Aura/Caratteristiche) per reggere questo innesto.")

        # 3. Verifica Slot Libero
        occupante = Oggetto.objects.filter(
            tracciamento_inventario__inventario=personaggio,
            tracciamento_inventario__data_fine__isnull=True,
            slot_corpo=slot,
            is_equipaggiato=True
        ).first()
        
        if occupante:
            raise ValidationError(f"Lo slot {slot} è già occupato da {occupante.nome}.")
            
        # 4. Esegui
        innesto.slot_corpo = slot
        innesto.is_equipaggiato = True
        innesto.save()
        
        personaggio.aggiungi_log(f"Installato {innesto.nome} nello slot {slot}.")
        return True
    
    
    @staticmethod
    def elabora_richiesta_assemblaggio(richiesta_id, esecutore):
        """
        Accetta la richiesta e avvia il lavoro SE l'artigiano è libero.
        """
        try: req = RichiestaAssemblaggio.objects.select_related('committente', 'artigiano', 'infusione').get(pk=richiesta_id)
        except: raise ValidationError("Richiesta non trovata.")

        if req.artigiano.proprietario != esecutore and not esecutore.is_staff:
             raise ValidationError("Non autorizzato.")
        if req.stato != STATO_RICHIESTA_PENDENTE: raise ValidationError("Già processata.")

        # --- NUOVO CONTROLLO: SLOT OCCUPATO ARTIGIANO ---
        if ForgiaturaInCorso.objects.filter(personaggio=req.artigiano).exists():
            raise ValidationError("Sei già occupato in una forgiatura. Completa il lavoro attuale prima di accettarne uno nuovo.")

        with transaction.atomic():
            # Pagamento
            if req.offerta_crediti > 0:
                if req.committente.crediti < req.offerta_crediti: raise ValidationError("Committente senza fondi.")
                req.committente.modifica_crediti(-req.offerta_crediti, f"Pagamento a {req.artigiano.nome}")
                req.artigiano.modifica_crediti(req.offerta_crediti, f"Lavoro da {req.committente.nome}")

            # Esecuzione
            if req.tipo_operazione == TIPO_OPERAZIONE_INNESTO:
                # Recupera la forgiatura
                if not req.forgiatura_target:
                    raise ValidationError("Forgiatura di riferimento mancante.")
                
                # Completa la forgiatura (crea l'oggetto per il committente)
                # Nota: Passiamo None come slot_scelto qui perché lo facciamo manualmente dopo
                # Ma wait, completa_forgiatura crea l'oggetto.
                # Dobbiamo passare l'artigiano come 'attore' per sbloccare il ritiro.
                
                # 1. Crea Oggetto (assegnato al Committente)
                nuovo_obj = GestioneCraftingService.completa_forgiatura(req.forgiatura_target.id, req.artigiano)
                
                # 2. Installa nello slot richiesto
                GestioneOggettiService.installa_innesto(req.committente, nuovo_obj, req.slot_destinazione)
                
                req.artigiano.aggiungi_log(f"Operazione completata: installato {nuovo_obj.nome} su {req.committente.nome}.")
            
            elif req.tipo_operazione == TIPO_OPERAZIONE_FORGIATURA:
                # Avvia timer (include check competenza cooperativa)
                GestioneCraftingService.avvia_forgiatura(
                    personaggio=req.artigiano, # Chi lavora (Aiutante)
                    infusione=req.infusione, 
                    destinatario_finale=req.committente, # Chi ha richiesto (Forgiatore)
                    is_academy=False,
                    aiutante=req.artigiano # Passiamo l'artigiano come aiutante esplicito
                )
                req.artigiano.aggiungi_log(f"Ha iniziato a forgiare {req.infusione.nome} per {req.committente.nome}.")
                
            elif req.tipo_operazione == TIPO_OPERAZIONE_RIMOZIONE:
                GestioneOggettiService.rimuovi_mod(req.artigiano, req.oggetto_host, req.componente)
            else:
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
        Verifica se il PG ha i requisiti per forgiare l'infusione.
        """
        livello_target = infusione.livello
        punteggi = forgiatore.caratteristiche_base # Default: forgiatore singolo
        
        # --- 1. CHECK AURA PRINCIPALE (Vincolo Forgiatore) ---
        if not infusione.aura_richiesta: 
            return False, "Infusione non valida (Manca Aura)."
            
        val_aura_main_f = forgiatore.get_valore_aura_effettivo(infusione.aura_richiesta)
        if val_aura_main_f < livello_target:
            return False, f"Il Forgiatore non ha l'Aura richiesta ({infusione.aura_richiesta.nome}) al livello necessario ({val_aura_main_f}/{livello_target})."

        # --- 2. GESTIONE AIUTANTE ---
        stats_f = forgiatore.caratteristiche_base
        stats_a = {}
        
        if aiutante:
            stats_a = aiutante.caratteristiche_base
            # Check requisiti base aiutante (deve avere un'aura valida)
            val_aura_main_a = aiutante.get_valore_aura_effettivo(infusione.aura_richiesta)
            has_valid_main = val_aura_main_a >= livello_target
            
            has_valid_sec = False
            if infusione.aura_infusione:
                val_aura_sec_a = aiutante.get_valore_aura_effettivo(infusione.aura_infusione)
                has_valid_sec = val_aura_sec_a >= livello_target
            
            if not (has_valid_main or has_valid_sec):
                return False, "L'Aiutante non possiede né l'Aura Richiesta né l'Aura Infusione al livello corretto."

        # --- 3. CHECK AURA SECONDARIA (Combinata: Max tra i due) ---
        if infusione.aura_infusione:
            val_f = forgiatore.get_valore_aura_effettivo(infusione.aura_infusione)
            val_a = aiutante.get_valore_aura_effettivo(infusione.aura_infusione) if aiutante else 0
            
            if max(val_f, val_a) < livello_target:
                return False, f"Livello Aura Infusione insufficiente ({infusione.aura_infusione.nome}). Max posseduto: {max(val_f, val_a)}/{livello_target}."

        # --- 4. CHECK CARATTERISTICHE (Combinata: Max tra i due) ---
        for comp in infusione.componenti.select_related('caratteristica').all():
            nome = comp.caratteristica.nome
            req_val = comp.valore
            
            val_f = stats_f.get(nome, 0)
            val_a = stats_a.get(nome, 0)
            
            if max(val_f, val_a) < req_val:
                return False, f"Caratteristica {nome} insufficiente. Max posseduto: {max(val_f, val_a)}/{req_val}."
                
        return True, "Requisiti soddisfatti."
    
    @staticmethod
    def get_valore_statistica_aura(personaggio, aura, campo):
        """Helper per leggere statistiche dinamiche dall'Aura."""
        stat = getattr(aura, campo, None)
        default = 60 if 'tempo' in campo else 100
        if not stat: return default
        val = personaggio.get_valore_statistica(stat.sigla)
        return max(1, val) if val > 0 else stat.valore_base_predefinito

    @staticmethod
    def calcola_costi_tempi(personaggio, infusione):
        """Restituisce (Costo Crediti, Durata Secondi)."""
        aura = infusione.aura_richiesta
        if not aura: return 0, 0
        
        c_unit = GestioneCraftingService.get_valore_statistica_aura(personaggio, aura, 'stat_costo_forgiatura')
        t_unit = GestioneCraftingService.get_valore_statistica_aura(personaggio, aura, 'stat_tempo_forgiatura')
        
        lvl = max(1, infusione.livello)
        return lvl * c_unit, lvl * t_unit

    @staticmethod
    def avvia_forgiatura(personaggio, infusione, slot_target=None, destinatario_finale=None, is_academy=False, aiutante=None):
        """
        Avvia il timer di crafting.
        """
        # --- 1. CONTROLLO SEQUENZIALITÀ (SLOT UNICO) ---
        # Se il personaggio ha già una forgiatura attiva (non completata/ritirata), non può iniziarne un'altra.
        if ForgiaturaInCorso.objects.filter(personaggio=personaggio).exists():
            raise ValidationError("Hai già una forgiatura in corso. Devi completarla e ritirare l'oggetto prima di iniziarne una nuova.")

        costo_da_pagare = 0
        descrizione_pagamento = ""
        
        # --- 2. GESTIONE COSTI E COMPETENZE ---
        if is_academy:
            costo_da_pagare = 200
            descrizione_pagamento = f"Servizio Accademia: {infusione.nome}"
        else:
            # Determina chi è il forgiatore principale per il controllo skill
            # Se c'è un destinatario (richiesta lavoro), LUI è il forgiatore, 'personaggio' (artigiano) è l'aiutante.
            # Se faccio da solo, forgiatore = personaggio, aiutante = None
            forgiatore = destinatario_finale if destinatario_finale else personaggio
            helper = personaggio if destinatario_finale else None
            
            can_do, msg = GestioneCraftingService.verifica_competenza_forgiatura(forgiatore, infusione, aiutante=helper)
            if not can_do: 
                raise ValidationError(f"Requisiti mancanti: {msg}")
            
            costo_mat, _ = GestioneCraftingService.calcola_costi_tempi(personaggio, infusione)
            costo_da_pagare = costo_mat
            descrizione_pagamento = f"Materiali forgiatura: {infusione.nome}"

        if personaggio.crediti < costo_da_pagare:
            raise ValidationError(f"Crediti insufficienti. Servono {costo_da_pagare} CR.")
            
        # --- 3. AVVIO TIMER ---
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
    def completa_forgiatura(task_id, attore, slot_scelto=None):
        """
        Termina il processo.
        Se slot_scelto è passato, tenta l'installazione immediata (Self-Install).
        """
        try:
            task = ForgiaturaInCorso.objects.get(pk=task_id)
        except ForgiaturaInCorso.DoesNotExist:
            raise ValidationError("Task non trovato.")
            
        # Verifica proprietà (Creatore o Destinatario)
        proprietario_finale = task.destinatario_finale if task.destinatario_finale else task.personaggio
        if attore.id != task.personaggio.id and attore.id != proprietario_finale.id:
            raise ValidationError("Non autorizzato.")
            
        if not task.is_pronta: raise ValidationError("Non ancora completata.")
        
        with transaction.atomic():
            # Crea oggetto
            nuovo_obj = GestioneOggettiService.crea_oggetto_da_infusione(task.infusione, proprietario_finale)
            
            # Se è richiesto il montaggio immediato (es. Innesto su se stesso)
            if slot_scelto:
                # Verifica che lo slot sia valido per questa infusione
                if task.infusione.slot_corpo_permessi and slot_scelto not in task.infusione.slot_corpo_permessi:
                    raise ValidationError(f"Slot {slot_scelto} non valido per questo oggetto.")
                
                # Installa
                GestioneOggettiService.installa_innesto(proprietario_finale, nuovo_obj, slot_scelto)
                
            # Se c'era uno slot target predefinito nel task (vecchia logica), usalo
            elif task.slot_target and proprietario_finale == attore:
                 GestioneOggettiService.installa_innesto(proprietario_finale, nuovo_obj, task.slot_target)

            task.delete()
            
            # Log
            if task.destinatario_finale:
                attore.aggiungi_log(f"Consegnato {nuovo_obj.nome} a {task.destinatario_finale.nome}.")
            else:
                attore.aggiungi_log(f"Ritirato {nuovo_obj.nome}.")
                
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
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
    """
    Gestisce la manipolazione fisica degli oggetti: creazione, assemblaggio, smontaggio.
    """

    @staticmethod
    def crea_oggetto_da_infusione(infusione, proprietario, nome_pers=None):
        """Factory: crea il record DB dell'oggetto (senza passare 'proprietario' al create)."""
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
        """ Gestisce l'installazione. """
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
            
        # [Logica compatibilità Materia/Mod omessa per brevità, assumiamo presente]

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
        """Gestisce lo smontaggio."""
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
    def elabora_richiesta_assemblaggio(richiesta_id, esecutore):
        """
        Accetta la richiesta. Avvia timer o esegue.
        """
        try: req = RichiestaAssemblaggio.objects.select_related('committente', 'artigiano', 'infusione').get(pk=richiesta_id)
        except: raise ValidationError("Richiesta non trovata.")

        if req.artigiano.proprietario != esecutore and not esecutore.is_staff:
             raise ValidationError("Non autorizzato.")
        if req.stato != STATO_RICHIESTA_PENDENTE: raise ValidationError("Già processata.")

        with transaction.atomic():
            if req.offerta_crediti > 0:
                if req.committente.crediti < req.offerta_crediti: raise ValidationError("Committente senza fondi.")
                req.committente.modifica_crediti(-req.offerta_crediti, f"Pagamento a {req.artigiano.nome}")
                req.artigiano.modifica_crediti(req.offerta_crediti, f"Lavoro da {req.committente.nome}")

            if req.tipo_operazione == TIPO_OPERAZIONE_FORGIATURA:
                # La richiesta definisce i ruoli:
                # Committente = Forgiatore (destinatario_finale)
                # Artigiano = Aiutante (personaggio che lavora)
                GestioneCraftingService.avvia_forgiatura(
                    personaggio=req.artigiano, 
                    infusione=req.infusione, 
                    destinatario_finale=req.committente,
                    is_academy=False
                )
                req.artigiano.aggiungi_log(f"Iniziata forgiatura {req.infusione.nome} per {req.committente.nome}.")
                
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
        Verifica i requisiti per la forgiatura, supportando la modalità cooperativa.
        
        REGOLE:
        1. Forgiatore (Committente): DEVE avere Aura Richiesta >= Livello.
        2. Aiutante (Artigiano): DEVE avere Aura Richiesta O Aura Infusione >= Livello.
        3. Combinata: Aura Infusione e Caratteristiche devono essere soddisfatte 
           da ALMENO UNO dei due (si usa il max).
        """
        livello = infusione.livello
        
        # --- 1. VALIDITÀ INFUSIONE ---
        if not infusione.aura_richiesta: 
            return False, "Infusione non valida (Manca Aura)."
            
        # --- 2. CHECK FORGIATORE (Principale) ---
        # "il Forgiatore DEVE avere l'aura richiesta del corretto livello"
        val_aura_main_f = forgiatore.get_valore_aura_effettivo(infusione.aura_richiesta)
        if val_aura_main_f < livello:
            return False, f"Il Forgiatore non ha l'Aura richiesta ({infusione.aura_richiesta.nome}) al livello necessario ({val_aura_main_f}/{livello})."

        # --- 3. CHECK AIUTANTE (Partecipazione) ---
        if aiutante:
            # "l'aiutante DEVE avere aura infusione o aura richiesta del livello corretto"
            val_aura_main_a = aiutante.get_valore_aura_effettivo(infusione.aura_richiesta)
            has_valid_main = val_aura_main_a >= livello
            
            has_valid_sec = False
            if infusione.aura_infusione:
                val_aura_sec_a = aiutante.get_valore_aura_effettivo(infusione.aura_infusione)
                has_valid_sec = val_aura_sec_a >= livello
            
            if not (has_valid_main or has_valid_sec):
                return False, "L'Aiutante non possiede né l'Aura Richiesta né l'Aura Infusione al livello corretto."

        # --- 4. CHECK AURA SECONDARIA (Combinata) ---
        if infusione.aura_infusione:
            val_f = forgiatore.get_valore_aura_effettivo(infusione.aura_infusione)
            val_a = aiutante.get_valore_aura_effettivo(infusione.aura_infusione) if aiutante else 0
            
            if max(val_f, val_a) < livello:
                return False, f"Aura Secondaria ({infusione.aura_infusione.nome}) insufficiente. Max posseduto: {max(val_f, val_a)}/{livello}."

        # --- 5. CHECK CARATTERISTICHE (Combinata) ---
        stats_f = forgiatore.caratteristiche_base
        stats_a = aiutante.caratteristiche_base if aiutante else {}
        
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
    def avvia_forgiatura(personaggio, infusione, slot_target=None, destinatario_finale=None, is_academy=False):
        """
        Avvia il timer di crafting.
        Gestisce correttamente i ruoli Forgiatore (Destinatario) e Aiutante (Esecutore).
        """
        costo_da_pagare = 0
        descrizione_pagamento = ""
        
        if is_academy:
            # ACCADEMIA: Costo fisso, ignora skill
            costo_da_pagare = 200
            descrizione_pagamento = f"Servizio Accademia: {infusione.nome}"
        else:
            # DETERMINAZIONE RUOLI PER VALIDAZIONE
            # Se c'è un destinatario_finale, stiamo lavorando per lui -> Lui è il Forgiatore
            if destinatario_finale:
                forgiatore = destinatario_finale
                aiutante = personaggio
            else:
                # Faccio da solo -> Io sono il Forgiatore, nessun aiutante
                forgiatore = personaggio
                aiutante = None

            # CHECK COMPETENZE
            can_do, msg = GestioneCraftingService.verifica_competenza_forgiatura(forgiatore, infusione, aiutante=aiutante)
            if not can_do: 
                raise ValidationError(msg)
            
            # COSTI MATERIALI (Paga chi esegue il lavoro, cioè 'personaggio')
            costo_mat, _ = GestioneCraftingService.calcola_costi_tempi(personaggio, infusione)
            costo_da_pagare = costo_mat
            descrizione_pagamento = f"Materiali forgiatura: {infusione.nome}"

        # Verifica Fondi (di chi esegue)
        if personaggio.crediti < costo_da_pagare:
            raise ValidationError(f"Crediti insufficienti. Servono {costo_da_pagare} CR.")
            
        # Calcolo Tempi
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
        """Termina il processo temporale e crea l'oggetto."""
        try:
            task = ForgiaturaInCorso.objects.get(pk=task_id, personaggio=attore)
        except ForgiaturaInCorso.DoesNotExist:
            raise ValidationError("Task non trovato.")
            
        if not task.is_pronta: 
            raise ValidationError("Forgiatura non ancora completata.")
        
        with transaction.atomic():
            proprietario = task.destinatario_finale if task.destinatario_finale else attore
            
            # Crea Fisicamente
            nuovo_obj = GestioneOggettiService.crea_oggetto_da_infusione(task.infusione, proprietario)
            
            # Equipaggia solo se forgiato per se stessi
            if task.slot_target and proprietario == attore:
                nuovo_obj.slot_corpo = task.slot_target
                nuovo_obj.is_equipaggiato = True
                nuovo_obj.save()
            
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
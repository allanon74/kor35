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
    TIPO_OPERAZIONE_FORGIATURA, TIPO_OPERAZIONE_RIMOZIONE, TIPO_OPERAZIONE_INSTALLAZIONE, TIPO_OPERAZIONE_INNESTO
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
        FIX: Rimosso proprietario dal create, aggiunto sposta_in_inventario.
        Include copia statistiche manuali e conversione mattoni.
        """
        
        # 1. Determina Tipo Oggetto dai flag dell'Aura
        tipo = TIPO_OGGETTO_FISICO
        aura = infusione.aura_richiesta
        if aura:
            if aura.produce_innesti: tipo = TIPO_OGGETTO_INNESTO
            elif aura.produce_mutazioni: tipo = TIPO_OGGETTO_MUTAZIONE
            elif aura.produce_mod: tipo = TIPO_OGGETTO_MOD
            elif aura.produce_materia: tipo = TIPO_OGGETTO_MATERIA
            # Fallback
            elif "tecnologic" in aura.nome.lower(): tipo = TIPO_OGGETTO_MOD
            elif "mondan" in aura.nome.lower(): tipo = TIPO_OGGETTO_MATERIA

        # 2. Crea l'Oggetto (Senza passare proprietario qui per evitare TypeError)
        nuovo_oggetto = Oggetto.objects.create(
            nome=nome_personalizzato or f"Manufatto di {infusione.nome}",
            tipo_oggetto=tipo,
            infusione_generatrice=infusione,
            is_tecnologico=(tipo in [TIPO_OGGETTO_MOD, TIPO_OGGETTO_INNESTO]),
            cariche_attuali=infusione.statistica_cariche.valore_predefinito if infusione.statistica_cariche else 0
        )

        # 3. Copia le Statistiche Base
        for stat_inf in infusione.infusionestatisticabase_set.all():
            OggettoStatisticaBase.objects.create(
                oggetto=nuovo_oggetto,
                statistica=stat_inf.statistica,
                valore_base=stat_inf.valore_base
            )

        # 4. Copia Modificatori Manuali (Definiti nell'Infusione)
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

        # 5. Copia Componenti & Conversione Mattoni
        for comp in infusione.componenti.select_related('caratteristica').all():
            OggettoCaratteristica.objects.create(
                oggetto=nuovo_oggetto,
                caratteristica=comp.caratteristica,
                valore=comp.valore
            )
            
            # Applica effetti del Mattone corrispondente
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
        
        # 6. Assegna al Personaggio
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
        L'artigiano accetta ed esegue la richiesta.
        """
        try: req = RichiestaAssemblaggio.objects.select_related('committente', 'artigiano', 'oggetto_host', 'componente', 'forgiatura_target').get(pk=richiesta_id)
        except: raise ValidationError("Richiesta non trovata.")

        if req.artigiano.proprietario != esecutore and not esecutore.is_staff:
            raise ValidationError("Non sei l'artigiano designato per questa richiesta.")
            
        if req.stato != STATO_RICHIESTA_PENDENTE: raise ValidationError("Richiesta già processata.")
        
        if req.tipo_operazione == TIPO_OPERAZIONE_FORGIATURA:
            if ForgiaturaInCorso.objects.filter(personaggio=req.artigiano).exists():
                raise ValidationError("Sei già occupato in una forgiatura.")

        with transaction.atomic():
            if req.offerta_crediti > 0:
                if req.committente.crediti < req.offerta_crediti: raise ValidationError("Il committente non ha più i crediti sufficienti.")
                req.committente.modifica_crediti(-req.offerta_crediti, f"Pagamento a {req.artigiano.nome}")
                req.artigiano.modifica_crediti(req.offerta_crediti, f"Lavoro da {req.committente.nome}")
            
            # DISPATCHER
            if req.tipo_operazione == TIPO_OPERAZIONE_FORGIATURA:
                GestioneCraftingService.avvia_forgiatura(
                    personaggio=req.artigiano, 
                    infusione=req.infusione, 
                    destinatario_finale=req.committente,
                    is_academy=False,
                    aiutante=req.artigiano
                )
                req.artigiano.aggiungi_log(f"Iniziata forgiatura {req.infusione.nome} per {req.committente.nome}.")
                
            elif req.tipo_operazione == TIPO_OPERAZIONE_INNESTO:
                 if not req.forgiatura_target: raise ValidationError("Forgiatura target mancante.")
                 nuovo_obj = GestioneCraftingService.completa_forgiatura(req.forgiatura_target.id, req.artigiano)
                 GestioneOggettiService.installa_innesto(req.committente, nuovo_obj, req.slot_destinazione)
                 req.artigiano.aggiungi_log(f"Operazione completata su {req.committente.nome}.")
                 
            elif req.tipo_operazione == TIPO_OPERAZIONE_RIMOZIONE:
                GestioneOggettiService.rimuovi_mod(req.artigiano, req.oggetto_host, req.componente)
            else:
                GestioneOggettiService.assembla_mod(req.artigiano, req.oggetto_host, req.componente)
            
            req.stato = STATO_RICHIESTA_COMPLETATA
            req.save()
        return True


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
        """Verifica requisiti cooperativi."""
        livello = infusione.livello
        if not infusione.aura_richiesta: return False, "Infusione non valida."
        
        # 1. Forgiatore
        val_f = forgiatore.get_valore_aura_effettivo(infusione.aura_richiesta)
        if val_f < livello: return False, f"Forgiatore: Aura insufficiente ({val_f}/{livello})."
        
        # 2. Aiutante (se presente)
        if aiutante:
            val_a = aiutante.get_valore_aura_effettivo(infusione.aura_richiesta)
            val_sec = 0
            if infusione.aura_infusione: val_sec = aiutante.get_valore_aura_effettivo(infusione.aura_infusione)
            if val_a < livello and val_sec < livello:
                return False, "Aiutante: Requisiti insufficienti."

        return True, "OK"

    @staticmethod
    def avvia_forgiatura(personaggio, infusione, slot_target=None, destinatario_finale=None, is_academy=False, aiutante=None):
        if ForgiaturaInCorso.objects.filter(personaggio=personaggio).exists():
            raise ValidationError("Hai già una forgiatura in corso.")

        costo_crediti = 0
        desc = ""
        
        if is_academy:
            costo_crediti = 200; desc = f"Accademia: {infusione.nome}"
        else:
            forgiatore = destinatario_finale if destinatario_finale else personaggio
            helper = aiutante if aiutante else (None if destinatario_finale else personaggio)
            # Se faccio da solo, helper = personaggio.
            if not helper: helper = personaggio
            
            can, msg = GestioneCraftingService.verifica_competenza_forgiatura(forgiatore, infusione, aiutante=helper if helper!=forgiatore else None)
            if not can: raise ValidationError(msg)

            c, _ = GestioneCraftingService.calcola_costi_forgiatura(personaggio, infusione)
            costo_crediti = c; desc = f"Materiali: {infusione.nome}"
        
        if personaggio.crediti < costo_crediti:
            raise ValidationError(f"Crediti insufficienti. Richiesti: {costo_crediti}")

        _, durata_secondi = GestioneCraftingService.calcola_costi_forgiatura(personaggio, infusione)
        fine_prevista = timezone.now() + timedelta(seconds=durata_secondi)

        with transaction.atomic():
            personaggio.modifica_crediti(-costo_crediti, desc)
            forgiatura = ForgiaturaInCorso.objects.create(
                personaggio=personaggio, 
                infusione=infusione, 
                data_fine_prevista=fine_prevista, 
                slot_target=slot_target,
                destinatario_finale=destinatario_finale
            )
            
        return forgiatura

    @staticmethod
    def completa_forgiatura(forgiatura_id, attore, slot_scelto=None):
        """
        Completa forgiatura.
        - Se slot_scelto è presente, tenta installazione immediata (Innesto).
        - Verifica che 'attore' sia il creatore o il destinatario.
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
            proprietario = task.destinatario_finale if task.destinatario_finale else task.personaggio
            nuovo_oggetto = GestioneOggettiService.crea_oggetto_da_infusione(task.infusione, proprietario)
            
            # Installazione Immediata (Innesto)
            if slot_scelto:
                GestioneOggettiService.installa_innesto(proprietario, nuovo_oggetto, slot_scelto)
            # Auto-equipaggiamento (Legacy)
            elif task.slot_target and proprietario.id == task.personaggio.id:
                nuovo_oggetto.slot_corpo = task.slot_target
                nuovo_oggetto.is_equipaggiato = True
                nuovo_oggetto.save()
            
            task.delete()
            
            if task.destinatario_finale:
                attore.aggiungi_log(f"Consegnato {nuovo_oggetto.nome} a {proprietario.nome}")
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

    
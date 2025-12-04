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
    STATO_RICHIESTA_PENDENTE, STATO_RICHIESTA_COMPLETATA, STATO_RICHIESTA_RIFIUTATA
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
    def crea_oggetto_da_infusione(infusione, proprietario, nome_personalizzato=None):
        """
        Metodo 'fabbrica' di basso livello. 
        Crea fisicamente l'istanza Oggetto copiando dati dall'Infusione.
        NON gestisce pagamenti o tempi (demandato a GestioneCraftingService o craft_oggetto_istantaneo).
        """
        if not infusione.aura_richiesta:
            raise ValidationError("Infusione non valida (manca Aura).")

        # 1. Determina il tipo
        tipo = TIPO_OGGETTO_FISICO
        aura_nome = infusione.aura_richiesta.nome.lower()
        if "tecnologic" in aura_nome: 
            tipo = TIPO_OGGETTO_MOD 
        elif "mondan" in aura_nome: 
            tipo = TIPO_OGGETTO_MATERIA
        # Aggiungi qui altre logiche per Innesti/Mutazioni se basate sull'aura

        # 2. Crea l'Oggetto
        nuovo_oggetto = Oggetto.objects.create(
            nome=nome_personalizzato or f"Manufatto di {infusione.nome}",
            tipo_oggetto=tipo,
            infusione_generatrice=infusione,
            is_tecnologico=(tipo in [TIPO_OGGETTO_MOD, TIPO_OGGETTO_INNESTO]),
            cariche_attuali=infusione.statistica_cariche.valore_predefinito if infusione.statistica_cariche else 0
        )

        # 3. Copia le Statistiche Base
        for stat_inf in infusione.infusionestatisticabase_set.all():
            OggettoStatistica.objects.create(
                oggetto=nuovo_oggetto,
                statistica=stat_inf.statistica,
                valore=stat_inf.valore_base,
                tipo_modificatore='ADD'
            )

        # 4. Copia le Caratteristiche (Componenti)
        for comp in infusione.componenti.all():
            OggettoCaratteristica.objects.create(
                oggetto=nuovo_oggetto,
                caratteristica=comp.caratteristica,
                valore=comp.valore
            )
        
        # 5. Assegna al Personaggio
        nuovo_oggetto.sposta_in_inventario(proprietario)
        
        return nuovo_oggetto

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
    def assembla_mod(assemblatore: Personaggio, oggetto_ospite: Oggetto, potenziamento: Oggetto, check_skills=True):
        """
        Gestisce l'installazione di Mod/Materia su un oggetto ospite.
        Unifica la logica di 'monta_potenziamento' e 'assembla_mod'.
        """
        
        # 1. Controlli di base e Proprietà
        proprietario_items = oggetto_ospite.inventario_corrente
        
        if not proprietario_items:
             raise ValidationError("Oggetto host non in inventario.")
        
        # Se stiamo processando una richiesta di lavoro, l'assemblatore può essere diverso dal proprietario.
        # Ma i due oggetti devono essere nello stesso posto (o gestiti dalla logica della richiesta).
        if potenziamento.inventario_corrente != proprietario_items:
             raise ValidationError("Host e Componente devono trovarsi nello stesso inventario.")

        if oggetto_ospite.pk == potenziamento.pk:
            raise ValidationError("Non puoi montare un oggetto su se stesso.")
        
        if potenziamento.ospitato_su:
            raise ValidationError("Il potenziamento è già montato altrove.")

        # 2. Check Skills
        if check_skills:
            can_do, msg = GestioneOggettiService.verifica_competenza_assemblaggio(assemblatore, oggetto_ospite, potenziamento)
            if not can_do:
                raise ValidationError(msg)

        classe = oggetto_ospite.classe_oggetto
        
        # --- LOGICA MATERIA ---
        if potenziamento.tipo_oggetto == TIPO_OGGETTO_MATERIA:
            if oggetto_ospite.is_tecnologico:
                 raise ValidationError("Le Materie non possono essere montate su oggetti Tecnologici.")

            # Check esclusività
            if oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MATERIA).exists():
                raise ValidationError("È già presente una Materia.")
            if oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD).exists():
                raise ValidationError("Impossibile installare Materia: presenti Mod.")
            
            if classe:
                # Recupera caratteristiche (ID) dalla Materia o dalla sua Infusione
                caratts_item = set(potenziamento.caratteristiche.values_list('id', flat=True))
                if not caratts_item and potenziamento.infusione_generatrice:
                     caratts_item = set(potenziamento.infusione_generatrice.componenti.values_list('caratteristica__id', flat=True))

                permessi_ids = set(classe.mattoni_materia_permessi.values_list('id', flat=True))
                
                # Debug Log
                print(f"DEBUG MATERIA: Host={oggetto_ospite.nome}, Materia={potenziamento.nome}, Caratts={caratts_item}, Permessi={permessi_ids}", file=sys.stderr)

                if not caratts_item.issubset(permessi_ids):
                     diff = caratts_item - permessi_ids
                     raise ValidationError(f"Questa Materia contiene caratteristiche non supportate dalla classe dell'oggetto (ID invalidi: {diff}).")

        # --- LOGICA MOD ---
        elif potenziamento.tipo_oggetto == TIPO_OGGETTO_MOD:
            if not oggetto_ospite.is_tecnologico:
                raise ValidationError("Le Mod richiedono un oggetto Tecnologico.")
            if oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MATERIA).exists():
                raise ValidationError("Impossibile installare Mod: presente Materia.")

            if not classe:
                raise ValidationError("Oggetto privo di Classe, impossibile montare Mod.")

            count_mods = oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD).count()
            if count_mods >= classe.max_mod_totali:
                raise ValidationError(f"Slot Mod esauriti (Max {classe.max_mod_totali}).")

            # Recupera caratteristiche Mod
            caratts_new = set(potenziamento.caratteristiche.values_list('id', flat=True))
            if not caratts_new and potenziamento.infusione_generatrice:
                 caratts_new = set(potenziamento.infusione_generatrice.componenti.values_list('caratteristica__id', flat=True))

            mods_installate = oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD)
            
            # Verifica regole specifiche per caratteristica (es. max 1 mod 'Ottica')
            for c_id in caratts_new:
                regola = classe.classi_oggetti_regole_mod.through.objects.filter(
                    classe_oggetto=classe, caratteristica_id=c_id
                ).first()
                
                max_allowed = regola.max_installabili if regola else 0
                if max_allowed == 0:
                    raise ValidationError(f"Mod con caratteristica ID {c_id} non permesse su {classe.nome}.")
                
                count_existing = 0
                for m in mods_installate:
                    m_caratts = set(m.caratteristiche.values_list('id', flat=True))
                    if not m_caratts and m.infusione_generatrice:
                        m_caratts = set(m.infusione_generatrice.componenti.values_list('caratteristica__id', flat=True))
                    
                    if c_id in m_caratts:
                        count_existing += 1
                
                if count_existing >= max_allowed:
                    raise ValidationError(f"Limite Mod per caratteristica ID {c_id} raggiunto ({count_existing}/{max_allowed}).")
        
        else:
             raise ValidationError("Tipo oggetto non supportato per l'assemblaggio (solo Mod o Materia).")

        # 3. ESECUZIONE
        with transaction.atomic():
            # Chiude tracciamento inventario precedente (rimuove dall'inventario visibile)
            potenziamento.sposta_in_inventario(None)
            
            # Assegna all'oggetto ospite
            potenziamento.ospitato_su = oggetto_ospite
            potenziamento.save()
            
            # Log
            if hasattr(proprietario_items, 'personaggio'):
                msg = f"Installato {potenziamento.nome} su {oggetto_ospite.nome}."
                if assemblatore != proprietario_items.personaggio:
                    msg += f" (Eseguito da {assemblatore.nome})"
                proprietario_items.personaggio.aggiungi_log(msg)

    @staticmethod
    def elabora_richiesta_assemblaggio(richiesta_id, artigiano_user):
        """
        L'artigiano accetta ed esegue la richiesta.
        """
        try:
            req = RichiestaAssemblaggio.objects.select_related('committente', 'artigiano', 'oggetto_host', 'componente').get(pk=richiesta_id)
        except RichiestaAssemblaggio.DoesNotExist:
            raise ValidationError("Richiesta non trovata.")

        if req.artigiano.proprietario != artigiano_user:
            raise ValidationError("Non sei l'artigiano designato per questa richiesta.")
            
        if req.stato != STATO_RICHIESTA_PENDENTE:
            raise ValidationError("Richiesta già processata.")

        # Verifica Disponibilità Crediti Committente
        if req.committente.crediti < req.offerta_crediti:
             raise ValidationError("Il committente non ha più i crediti sufficienti.")

        # ESECUZIONE
        with transaction.atomic():
            # 1. Esegui Assemblaggio (usando l'artigiano come esecutore per i check skill)
            GestioneOggettiService.assembla_mod(req.artigiano, req.oggetto_host, req.componente, check_skills=True)
            
            # 2. Transazione Crediti
            if req.offerta_crediti > 0:
                req.committente.modifica_crediti(-req.offerta_crediti, f"Pagamento assemblaggio a {req.artigiano.nome}")
                req.artigiano.modifica_crediti(req.offerta_crediti, f"Compenso assemblaggio da {req.committente.nome}")
            
            # 3. Aggiorna stato
            req.stato = STATO_RICHIESTA_COMPLETATA
            req.save()
            
            # 4. Log
            req.committente.aggiungi_log(f"Richiesta completata: {req.artigiano.nome} ha assemblato {req.componente.nome}.")
            req.artigiano.aggiungi_log(f"Lavoro completato per {req.committente.nome}.")

        return True

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


class GestioneCraftingService:
    """
    Gestisce i processi temporali e i costi di forgiatura.
    Si appoggia a GestioneOggettiService per la creazione fisica degli item.
    """

    @staticmethod
    def get_valore_statistica_aura(personaggio, aura, campo_configurazione):
        statistica_ref = getattr(aura, campo_configurazione, None)
        DEFAULT_COSTO = 100
        DEFAULT_TEMPO = 60
        
        if not statistica_ref:
            if 'tempo' in campo_configurazione: return DEFAULT_TEMPO
            return DEFAULT_COSTO

        valore = personaggio.get_valore_statistica(statistica_ref.sigla) 
        if valore <= 0:
            valore = statistica_ref.valore_base_predefinito
            
        return max(1, valore)

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
    def avvia_forgiatura(personaggio, infusione_id, slot_target=None):
        infusione = Infusione.objects.get(pk=infusione_id)
        
        is_valid, msg = personaggio.valida_acquisto_tecnica(infusione)
        if not is_valid: # Check basico (es. auree conosciute)
             pass # O raise ValidationError(msg) se vuoi essere stretto
        
        if not personaggio.infusioni_possedute.filter(pk=infusione_id).exists():
             raise ValidationError("Non conosci questa infusione.")

        costo_crediti, durata_secondi = GestioneCraftingService.calcola_costi_forgiatura(personaggio, infusione)
        
        if personaggio.crediti < costo_crediti:
            raise ValidationError(f"Crediti insufficienti. Richiesti: {costo_crediti}")

        with transaction.atomic():
            personaggio.modifica_crediti(-costo_crediti, f"Avvio forgiatura: {infusione.nome}")
            fine_prevista = timezone.now() + timedelta(seconds=durata_secondi)
            forgiatura = ForgiaturaInCorso.objects.create(
                personaggio=personaggio, 
                infusione=infusione, 
                data_fine_prevista=fine_prevista, 
                slot_target=slot_target
            )
            
        return forgiatura

    @staticmethod
    def completa_forgiatura(forgiatura_id, personaggio):
        try:
            task = ForgiaturaInCorso.objects.get(pk=forgiatura_id, personaggio=personaggio)
        except ForgiaturaInCorso.DoesNotExist:
            raise ValidationError("Forgiatura non trovata.")
            
        if not task.is_pronta:
            raise ValidationError("La forgiatura non è ancora completata.")
            
        if task.completata:
             raise ValidationError("Oggetto già ritirato.")
        
        with transaction.atomic():
            # USA IL METODO UNIFICATO IN GestioneOggettiService
            nuovo_oggetto = GestioneOggettiService.crea_oggetto_da_infusione(task.infusione, personaggio)
            
            if task.slot_target:
                nuovo_oggetto.slot_corpo = task.slot_target
                nuovo_oggetto.is_equipaggiato = True
                nuovo_oggetto.save()
            
            task.delete() # Rimuove il task dalla coda
            personaggio.aggiungi_log(f"Forgiatura completata: {nuovo_oggetto.nome}")
            
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
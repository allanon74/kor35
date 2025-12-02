# personaggi/services.py

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import (
    Oggetto, Infusione, Mattone, Personaggio, OggettoInInventario, 
    TIPO_OGGETTO_FISICO, TIPO_OGGETTO_MOD, TIPO_OGGETTO_MATERIA, 
    TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE,
    COSTO_PER_MATTONE_OGGETTO, QrCode, OggettoStatistica, Inventario,
    OggettoBase, OggettoStatisticaBase, 
    ForgiaturaInCorso, 
)

def crea_oggetto_da_infusione(infusione, personaggio, nome_personalizzato=None):
    """
    Crea un'istanza fisica (Oggetto) a partire da un'Infusione (Crafting).
    Trasforma le 'Statistiche Base' dell'infusione in 'Modificatori' dell'oggetto.
    """
    if not infusione.aura_richiesta:
        raise ValidationError("Infusione non valida (manca Aura).")

    # 1. Determina il tipo di oggetto in base all'Aura
    # Logica personalizzabile: es. Aura Tecnologica -> Mod/Innesto, Mondana -> Materia
    tipo = TIPO_OGGETTO_FISICO
    aura_nome = infusione.aura_richiesta.nome.lower()
    
    if "tecnologic" in aura_nome:
        # Qui potresti distinguere tra MOD e INNESTO in base a qualche flag dell'infusione
        # Per ora defaultiamo a MOD, o potresti passare il tipo come argomento
        tipo = TIPO_OGGETTO_MOD 
    elif "mondan" in aura_nome: # O Trasmutazione
        tipo = TIPO_OGGETTO_MATERIA
    
    # 2. Crea l'Oggetto
    nuovo_oggetto = Oggetto.objects.create(
        nome=nome_personalizzato or f"Manufatto di {infusione.nome}",
        tipo_oggetto=tipo,
        infusione_generatrice=infusione,
        is_tecnologico=(tipo in [TIPO_OGGETTO_MOD, 'INN']), # Flag tech
        cariche_attuali=infusione.statistica_cariche.valore_predefinito if infusione.statistica_cariche else 0
    )

    # 3. Copia le Statistiche
    # IMPORTANTE: Le StatBase dell'infusione diventano MODIFICATORI (OggettoStatistica) del nuovo oggetto.
    # Questo perché una Mod deve fornire un +1 (Modificatore) all'arma che la ospita.
    for stat_inf in infusione.infusionestatisticabase_set.all():
        OggettoStatistica.objects.create(
            oggetto=nuovo_oggetto,
            statistica=stat_inf.statistica,
            valore=stat_inf.valore_base,
            tipo_modificatore='ADD' # Defaultiamo ad additivo, o rendilo configurabile
        )
    
    # 4. Assegna al Personaggio
    nuovo_oggetto.sposta_in_inventario(personaggio)
    
    return nuovo_oggetto


def monta_potenziamento(oggetto_ospite, potenziamento):
    """
    Gestisce l'installazione di Mod/Materia su un oggetto ospite.
    Controlla compatibilità, slot liberi e limiti per caratteristica.
    """
    
    # A. Validazioni Base
    if oggetto_ospite.pk == potenziamento.pk:
        raise ValidationError("Non puoi montare un oggetto su se stesso.")
    if potenziamento.ospitato_su:
        raise ValidationError("Il potenziamento è già montato altrove.")

    # B. Logica MATERIA
    if potenziamento.tipo_oggetto == TIPO_OGGETTO_MATERIA:
        if oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MATERIA).exists():
            raise ValidationError("È già presente una Materia.")
        if oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD).exists():
            raise ValidationError("Impossibile installare Materia: presenti Mod.")
        
        # Check Classe Oggetto: Mattoni Permessi per Materia
        if oggetto_ospite.classe_oggetto:
            # Recupera le caratteristiche dei mattoni dell'infusione
            if potenziamento.infusione_generatrice:
                caratts_infusione = set(potenziamento.infusione_generatrice.mattoni.values_list('caratteristica_associata', flat=True))
                permessi_ids = set(oggetto_ospite.classe_oggetto.mattoni_materia_permessi.values_list('id', flat=True))
                
                # Se l'infusione ha ANCHE SOLO UNA caratteristica non permessa, blocca? 
                # O deve averne ALMENO UNA permessa? Di solito è restrittivo (tutte devono essere ok).
                if not caratts_infusione.issubset(permessi_ids):
                     raise ValidationError("Questa Materia contiene caratteristiche non compatibili con questo oggetto.")

    # C. Logica MOD
    elif potenziamento.tipo_oggetto == TIPO_OGGETTO_MOD:
        if not oggetto_ospite.is_tecnologico:
            raise ValidationError("Le Mod richiedono un oggetto Tecnologico.")
        if oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MATERIA).exists():
            raise ValidationError("Impossibile installare Mod: presente Materia.")

        classe = oggetto_ospite.classe_oggetto
        if not classe:
            raise ValidationError("Oggetto privo di Classe, impossibile montare Mod.")

        # 1. Check Limite Totale
        count_mods = oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD).count()
        if count_mods >= classe.max_mod_totali:
            raise ValidationError(f"Slot Mod esauriti (Max {classe.max_mod_totali}).")

        # 2. Check Limite per Caratteristica (Cruciale!)
        infusione = potenziamento.infusione_generatrice
        if infusione:
            # Caratteristiche della NUOVA mod
            caratts_new = set(infusione.mattoni.values_list('caratteristica_associata', flat=True))
            
            # Caratteristiche delle mod GIÀ installate
            mods_installate = oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD)
            
            for c_id in caratts_new:
                # Recupera il limite dalla tabella through
                regola = classe.limitazioni_mod.through.objects.filter(
                    classe_oggetto=classe, caratteristica_id=c_id
                ).first()
                
                max_allowed = regola.max_installabili if regola else 0
                if max_allowed == 0:
                    raise ValidationError(f"Mod con caratteristica ID {c_id} non permesse su {classe.nome}.")
                
                # Conta quante mod installate hanno QUESTA caratteristica
                count_existing = 0
                for m in mods_installate:
                    if m.infusione_generatrice and m.infusione_generatrice.mattoni.filter(caratteristica_associata_id=c_id).exists():
                        count_existing += 1
                
                if count_existing >= max_allowed:
                    raise ValidationError(f"Limite Mod per caratteristica ID {c_id} raggiunto ({count_existing}/{max_allowed}).")

    # D. Esecuzione (Atomica)
    with transaction.atomic():
        # Rimuovi dall'inventario "fisico" (chiudi tracciamento)
        # Nota: assumiamo che 'tracciamento_inventario' sia il related_name in OggettoInInventario
        tracc = potenziamento.tracciamento_inventario.filter(data_fine__isnull=True).first()
        if tracc:
            tracc.data_fine = timezone.now()
            tracc.save()
            
        potenziamento.ospitato_su = oggetto_ospite
        potenziamento.save()
        
class GestioneOggettiService:
    
    @staticmethod
    def calcola_cog_utilizzata(pg: Personaggio):
        """Calcola la Capacità Oggetti (COG) attualmente occupata."""
        # Recupera oggetti nell'inventario corrente del PG
        oggetti = pg.get_oggetti().filter(
            # Filtra solo quelli che "pesano" sulla COG
            # 1. Oggetti Fisici Equipaggiati
            # 2. Innesti e Mutazioni (sempre equipaggiati se posseduti/installati)
        )
        
        cog_totale = 0
        for obj in oggetti:
            if obj.tipo_oggetto in [TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE]:
                cog_totale += 1
            elif obj.tipo_oggetto == TIPO_OGGETTO_FISICO and obj.is_equipaggiato:
                # Un oggetto fisico conta 1 se equipaggiato (o logica più complessa se pesa di più)
                cog_totale += 1
                
        return cog_totale

    @staticmethod
    def verifica_consenso(target: Personaggio, qrcode_id: str):
        """Verifica se il QR code appartiene al target (per operazioni su altri)."""
        try:
            qr = QrCode.objects.get(id=qrcode_id)
            # Logica: Il QR deve puntare al Personaggio target (tramite vista)
            if qr.vista and hasattr(qr.vista, 'personaggio') and qr.vista.personaggio == target:
                return True
            return False
        except QrCode.DoesNotExist:
            return False

    @staticmethod
    def craft_oggetto(crafter: Personaggio, infusione: Infusione, target: Personaggio = None, qrcode_id: str = None):
        """
        Gestisce la creazione di QUALSIASI oggetto da Infusione (Fisico, Mod, Materia, Innesto, Mutazione).
        """
        target = target or crafter # Se target è None, è self-cast
        
        # 1. Determina Tipo e Aura Richiesta dal Crafter
        tipo_output = TIPO_OGGETTO_FISICO # Default
        aura_richiesta_craft = "Aura Mondana - Trasmutatore" # Esempio nome
        costo_base = COSTO_PER_MATTONE_OGGETTO
        
        # Logica euristica per capire il tipo dall'infusione (o dai tag dell'infusione)
        # Qui assumiamo che l'infusione abbia un modo per dirci cosa crea, oppure lo deduciamo dall'aura richiesta
        if "Tecnologica" in infusione.aura_richiesta.nome:
            aura_richiesta_craft = "Aura Tecnologica"
            # Se ha slot corpo è un innesto, altrimenti Mod (semplificazione)
            # Bisognerebbe aggiungere un campo 'tipo_risultato' a Infusione per essere precisi
            tipo_output = TIPO_OGGETTO_MOD 
            
        elif "Innata" in infusione.aura_richiesta.nome:
            aura_richiesta_craft = "Aura Innata"
            tipo_output = TIPO_OGGETTO_MUTAZIONE

        # 2. Verifica Livello Aura del Crafter
        livello_aura_crafter = crafter.get_valore_aura_effettivo_by_name(aura_richiesta_craft) # Da implementare helper
        if infusione.livello > livello_aura_crafter:
            raise ValidationError(f"Livello Aura insufficiente. Richiesto: {infusione.livello}, Hai: {livello_aura_crafter}")

        # 3. Verifica Requisiti Mattoni (Caratteristiche)
        # I requisiti dei mattoni dell'infusione devono essere soddisfatti dal Crafter
        # (Logica già presente in valida_acquisto_tecnica, riutilizzabile)

        # 4. Verifica Consenso e Installazione Immediata (Innesti/Mutazioni)
        if tipo_output in [TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE]:
            if target != crafter:
                if not qrcode_id or not GestioneOggettiService.verifica_consenso(target, qrcode_id):
                    raise ValidationError("Consenso del bersaglio mancante o QR non valido.")
            
            # Verifica Slot Libero (Solo per Innesti)
            # Implementare logica per determinare lo slot target dall'infusione
            
            # Verifica COG Target
            cog_used = GestioneOggettiService.calcola_cog_utilizzata(target)
            cog_max = target.get_valore_statistica('COG') # Assumiamo esista statistica COG
            if cog_used >= cog_max:
                raise ValidationError("Capacità Oggetti del bersaglio esaurita.")

        # 5. Pagamento
        costo_totale = infusione.livello * costo_base
        if crafter.crediti < costo_totale:
            raise ValidationError("Crediti insufficienti.")
        crafter.modifica_crediti(-costo_totale, f"Creazione {infusione.nome}")

        # 6. Creazione Oggetto
        with transaction.atomic():
            nuovo_oggetto = Oggetto.objects.create(
                nome=infusione.nome,
                testo=infusione.testo,
                tipo_oggetto=tipo_output,
                infusione_generatrice=infusione,
                aura=infusione.aura_infusione, # L'aura dell'oggetto è quella infusa
                # ... altri campi copiati dall'infusione ...
            )
            
            # Assegna statistiche base
            for stat_link in infusione.infusionestatisticabase_set.all():
                nuovo_oggetto.statistiche_base.add(
                    stat_link.statistica, 
                    through_defaults={'valore_base': stat_link.valore_base}
                )

            # Assegna al target (tramite tracciamento inventario)
            nuovo_oggetto.sposta_in_inventario(target) # target è un Personaggio (che è un Inventario)
            
            # Se Innesto/Mutazione, equipaggia subito
            if tipo_output in [TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE]:
                # Qui dovresti mappare lo slot dall'infusione all'oggetto
                # nuovo_oggetto.slot_corpo = ... 
                nuovo_oggetto.is_equipaggiato = True # Gli innesti nascono equipaggiati
                nuovo_oggetto.save()

        return nuovo_oggetto

    @staticmethod
    def assembla_mod(assemblatore: Personaggio, oggetto_host: Oggetto, mod: Oggetto):
        """
        Monta una MOD (o Materia) su un oggetto ospite.
        """
        # 1. Verifiche di Possesso
        if oggetto_host.inventario_corrente != assemblatore or mod.inventario_corrente != assemblatore:
            raise ValidationError("Devi possedere entrambi gli oggetti.")

        # 2. Verifica Aura Assemblatore
        aura_nec = "Aura Tecnologica" if mod.tipo_oggetto == TIPO_OGGETTO_MOD else "Aura Mondana - Assemblatore"
        liv_aura = assemblatore.get_valore_aura_effettivo_by_name(aura_nec)
        if mod.livello > liv_aura:
             raise ValidationError(f"Livello {aura_nec} insufficiente per assemblare questa mod.")

        # 3. Verifica Regole Classe Oggetto (Compatibilità)
        classe = oggetto_host.classe_oggetto
        if not classe:
            raise ValidationError("L'oggetto ospite non ha una classe definita, non può essere modificato.")

        # Esempio check limite totale mod
        num_mod_attuali = oggetto_host.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD).count()
        if mod.tipo_oggetto == TIPO_OGGETTO_MOD and num_mod_attuali >= classe.max_mod_totali:
             raise ValidationError("Slot Mod esauriti su questo oggetto.")
        
        # 4. Esegui Assemblaggio
        with transaction.atomic():
            mod.ospitato_su = oggetto_host
            mod.sposta_in_inventario(None) # Rimuovi dall'inventario "a terra", ora è dentro l'oggetto
            mod.save()

    @staticmethod
    def equipaggia_oggetto(personaggio: Personaggio, oggetto: Oggetto):
        """
        Attiva/Equipaggia un oggetto fisico (arma/armatura).
        """
        # Recupera l'inventario attuale dell'oggetto
        inv_corrente = oggetto.inventario_corrente
        
        # Verifica rigorosa tramite ID:
        # L'oggetto deve avere un inventario E l'ID dell'inventario deve corrispondere al personaggio
        if not inv_corrente or inv_corrente.id != personaggio.id:
             raise ValidationError(f"Non possiedi l'oggetto '{oggetto.nome}'. Si trova in: {inv_corrente.nome if inv_corrente else 'Nessun luogo'}")
        
        # ... (il resto del codice rimane uguale: controllo equipaggiato, controllo COG, ecc.)
        if oggetto.is_equipaggiato:
            oggetto.is_equipaggiato = False
            oggetto.save()
            return "Disequipaggiato"
        
        # Sta provando a equipaggiare: Check COG
        cog_used = GestioneOggettiService.calcola_cog_utilizzata(personaggio)
        cog_max = personaggio.get_valore_statistica('COG')
        
        if cog_used >= cog_max:
             raise ValidationError(f"Capacità Oggetti raggiunta ({cog_used}/{cog_max}). Libera slot prima.")
        
        oggetto.is_equipaggiato = True
        oggetto.save()
        return "Equipaggiato"
    
    
class GestioneCraftingService:

    @staticmethod
    def get_valore_statistica_aura(personaggio, aura, campo_configurazione):
        """
        Recupera il valore della statistica associata all'aura per una certa operazione.
        Esempio: aura.stat_tempo_forgiatura -> 'Velocità Forgia' -> Valore PG.
        Se non configurata, ritorna un default (es. 100 o 60).
        """
        statistica_ref = getattr(aura, campo_configurazione, None)
        
        # Default se l'admin non ha configurato l'aura
        DEFAULT_COSTO = 100
        DEFAULT_TEMPO = 60 # secondi
        
        if not statistica_ref:
            if 'tempo' in campo_configurazione: return DEFAULT_TEMPO
            return DEFAULT_COSTO

        # Recupera il valore effettivo dal personaggio (Base + Modificatori)
        # Assumiamo che il 'parametro' della statistica sia quello usato per i calcoli
        valore = personaggio.get_valore_statistica(statistica_ref.sigla) 
        
        # Se la statistica non è trovata o è 0, usiamo il valore base della statistica stessa
        if valore <= 0:
            valore = statistica_ref.valore_base_predefinito
            
        return max(1, valore) # Evitiamo divisioni per zero o costi negativi

    @staticmethod
    def calcola_costi_forgiatura(personaggio, infusione):
        aura = infusione.aura_richiesta
        if not aura: return 0, 0 # Fallback
        
        # 1. Recupera costo per mattone dalla configurazione Aura
        costo_per_mattone = GestioneCraftingService.get_valore_statistica_aura(
            personaggio, aura, 'stat_costo_forgiatura'
        )
        
        # 2. Recupera tempo per mattone dalla configurazione Aura
        tempo_per_mattone = GestioneCraftingService.get_valore_statistica_aura(
            personaggio, aura, 'stat_tempo_forgiatura'
        )
        
        livello = infusione.livello
        if livello == 0: livello = 1 # Minimo 1 per i calcoli base
        
        costo_totale = livello * costo_per_mattone
        tempo_totale = livello * tempo_per_mattone
        
        return costo_totale, tempo_totale

    @staticmethod
    def avvia_forgiatura(personaggio, infusione_id, slot_target=None):
        infusione = Infusione.objects.get(pk=infusione_id)
        
        # 1. Validazioni
        is_valid, msg = personaggio.valida_acquisto_tecnica(infusione)
        # Nota: Qui potresti voler saltare la validazione se l'ha già acquisita, 
        # ma controlliamo se possiede i requisiti per usarla ora.
        
        if not personaggio.infusioni_possedute.filter(pk=infusione_id).exists():
             raise ValidationError("Non conosci questa infusione.")

        # 2. Calcolo Costi e Tempi Dinamici
        costo_crediti, durata_secondi = GestioneCraftingService.calcola_costi_forgiatura(personaggio, infusione)
        
        if personaggio.crediti < costo_crediti:
            raise ValidationError(f"Crediti insufficienti. Richiesti: {costo_crediti}")

        # 3. Transazione
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

        # Creazione Oggetto (Usiamo il servizio esistente o logica simile)
        from .services import crea_oggetto_da_infusione # Importa la funzione helper esistente
        
        with transaction.atomic():
            # Crea fisicamente l'oggetto
            # Nota: Passiamo None come target iniziale, poi lo spostiamo noi per sicurezza
            nuovo_oggetto = crea_oggetto_da_infusione(task.infusione, personaggio)
            
            # Se c'era uno slot target (es. Innesti), gestisci equipaggiamento
            if task.slot_target:
                nuovo_oggetto.slot_corpo = task.slot_target
                nuovo_oggetto.is_equipaggiato = True # Innesti nascono equipaggiati
                nuovo_oggetto.save()
            
            # Elimina il task (o segnalo completato per lo storico)
            task.delete()
            
            personaggio.aggiungi_log(f"Forgiatura completata: {nuovo_oggetto.nome}")
            
        return nuovo_oggetto

    @staticmethod
    def acquista_da_negozio(personaggio, oggetto_base_id):
        """
        Crea un Oggetto reale a partire da un OggettoBase (Template).
        """
        try:
            template = OggettoBase.objects.get(pk=oggetto_base_id)
        except OggettoBase.DoesNotExist:
            raise ValidationError("Oggetto non trovato nel listino.")
            
        if not template.in_vendita:
            raise ValidationError("Questo oggetto non è più in vendita.")
            
        costo = template.costo
        
        # Sconti (Opzionale: qui puoi applicare la logica RCO - Riduzione Costo Oggetti)
        # sconto_perc = personaggio.get_valore_statistica('RCO')
        # costo = int(costo * (1 - sconto_perc/100))
        
        if personaggio.crediti < costo:
            raise ValidationError(f"Crediti insufficienti. Costo: {costo}")
            
        with transaction.atomic():
            personaggio.modifica_crediti(-costo, f"Acquisto negozio: {template.nome}")
            
            # ISTANZIAZIONE DELL'OGGETTO
            nuovo_oggetto = Oggetto.objects.create(
                nome=template.nome,
                testo=template.descrizione, # Copia la descrizione statica
                tipo_oggetto=template.tipo_oggetto,
                classe_oggetto=template.classe_oggetto,
                is_tecnologico=template.is_tecnologico,
                costo_acquisto=costo, # Salviamo quanto è stato pagato
                attacco_base=template.attacco_base,
                
                # Riferimenti
                oggetto_base_generatore=template,
                
                # Default
                in_vendita=False,
                is_equipaggiato=False,
                cariche_attuali=0 # Default, gli oggetti base non hanno cariche di solito
            )
            
            # COPIA STATISTICHE BASE (Es. Valore Armatura, Danno)
            for stat_link in template.oggettobasestatisticabase_set.all():
                OggettoStatisticaBase.objects.create(
                    oggetto=nuovo_oggetto,
                    statistica=stat_link.statistica,
                    valore_base=stat_link.valore_base
                )

            # COPIA MODIFICATORI (Es. +1 a Forza)
            for mod_link in template.oggettobasemodificatore_set.all():
                OggettoStatistica.objects.create(
                    oggetto=nuovo_oggetto,
                    statistica=mod_link.statistica,
                    valore=mod_link.valore,
                    tipo_modificatore=mod_link.tipo_modificatore
                )
                
            # Assegna all'inventario del PG
            nuovo_oggetto.sposta_in_inventario(personaggio)
            
        return nuovo_oggetto
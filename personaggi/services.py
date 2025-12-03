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
    tipo = TIPO_OGGETTO_FISICO
    aura_nome = infusione.aura_richiesta.nome.lower()
    
    if "tecnologic" in aura_nome:
        tipo = TIPO_OGGETTO_MOD 
    elif "mondan" in aura_nome:
        tipo = TIPO_OGGETTO_MATERIA
    
    # 2. Crea l'Oggetto
    nuovo_oggetto = Oggetto.objects.create(
        nome=nome_personalizzato or f"Manufatto di {infusione.nome}",
        tipo_oggetto=tipo,
        infusione_generatrice=infusione,
        is_tecnologico=(tipo in [TIPO_OGGETTO_MOD, 'INN']),
        cariche_attuali=infusione.statistica_cariche.valore_predefinito if infusione.statistica_cariche else 0
    )

    # 3. Copia le Statistiche
    for stat_inf in infusione.infusionestatisticabase_set.all():
        OggettoStatistica.objects.create(
            oggetto=nuovo_oggetto,
            statistica=stat_inf.statistica,
            valore=stat_inf.valore_base,
            tipo_modificatore='ADD'
        )
    
    # 4. Assegna al Personaggio
    nuovo_oggetto.sposta_in_inventario(personaggio)
    
    return nuovo_oggetto


def monta_potenziamento(oggetto_ospite, potenziamento):
    """
    Gestisce l'installazione di Mod/Materia su un oggetto ospite.
    """
    
    if oggetto_ospite.pk == potenziamento.pk:
        raise ValidationError("Non puoi montare un oggetto su se stesso.")
    if potenziamento.ospitato_su:
        raise ValidationError("Il potenziamento è già montato altrove.")

    if potenziamento.tipo_oggetto == TIPO_OGGETTO_MATERIA:
        if oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MATERIA).exists():
            raise ValidationError("È già presente una Materia.")
        if oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD).exists():
            raise ValidationError("Impossibile installare Materia: presenti Mod.")
        
        if oggetto_ospite.classe_oggetto:
            if potenziamento.infusione_generatrice:
                caratts_infusione = set(potenziamento.infusione_generatrice.caratteristiche.values_list('id', flat=True))
                permessi_ids = set(oggetto_ospite.classe_oggetto.mattoni_materia_permessi.values_list('id', flat=True))
                
                if not caratts_infusione.issubset(permessi_ids):
                     raise ValidationError("Questa Materia contiene caratteristiche non compatibili con questo oggetto.")

    elif potenziamento.tipo_oggetto == TIPO_OGGETTO_MOD:
        if not oggetto_ospite.is_tecnologico:
            raise ValidationError("Le Mod richiedono un oggetto Tecnologico.")
        if oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MATERIA).exists():
            raise ValidationError("Impossibile installare Mod: presente Materia.")

        classe = oggetto_ospite.classe_oggetto
        if not classe:
            raise ValidationError("Oggetto privo di Classe, impossibile montare Mod.")

        count_mods = oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD).count()
        if count_mods >= classe.max_mod_totali:
            raise ValidationError(f"Slot Mod esauriti (Max {classe.max_mod_totali}).")

        infusione = potenziamento.infusione_generatrice
        if infusione:
            caratts_new = set(infusione.caratteristiche.values_list('id', flat=True))
            mods_installate = oggetto_ospite.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD)
            
            for c_id in caratts_new:
                regola = classe.limitazioni_mod.through.objects.filter(
                    classe_oggetto=classe, caratteristica_id=c_id
                ).first()
                
                max_allowed = regola.max_installabili if regola else 0
                if max_allowed == 0:
                    raise ValidationError(f"Mod con caratteristica ID {c_id} non permesse su {classe.nome}.")
                
                count_existing = 0
                for m in mods_installate:
                    if m.infusione_generatrice and m.infusione_generatrice.caratteristiche.filter(id=c_id).exists():
                        count_existing += 1
                
                if count_existing >= max_allowed:
                    raise ValidationError(f"Limite Mod per caratteristica ID {c_id} raggiunto ({count_existing}/{max_allowed}).")

    with transaction.atomic():
        tracc = potenziamento.tracciamento_inventario.filter(data_fine__isnull=True).first()
        if tracc:
            tracc.data_fine = timezone.now()
            tracc.save()
            
        potenziamento.ospitato_su = oggetto_ospite
        potenziamento.save()
        
class GestioneOggettiService:
    
    @staticmethod
    def calcola_cog_utilizzata(pg: Personaggio):
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
    def craft_oggetto(crafter: Personaggio, infusione: Infusione, target: Personaggio = None, qrcode_id: str = None):
        target = target or crafter 
        tipo_output = TIPO_OGGETTO_FISICO 
        
        # Logica euristica tipo
        if "Tecnologica" in infusione.aura_richiesta.nome:
            tipo_output = TIPO_OGGETTO_MOD 
        elif "Innata" in infusione.aura_richiesta.nome:
            tipo_output = TIPO_OGGETTO_MUTAZIONE

        if tipo_output in [TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE]:
            if target != crafter:
                if not qrcode_id or not GestioneOggettiService.verifica_consenso(target, qrcode_id):
                    raise ValidationError("Consenso del bersaglio mancante o QR non valido.")
            
            cog_used = GestioneOggettiService.calcola_cog_utilizzata(target)
            cog_max = target.get_valore_statistica('COG')
            if cog_used >= cog_max:
                raise ValidationError("Capacità Oggetti del bersaglio esaurita.")

        # CALCOLO COSTO DINAMICO
        costo_base = COSTO_PER_MATTONE_OGGETTO
        if infusione.aura_richiesta and infusione.aura_richiesta.stat_costo_forgiatura:
             val = infusione.aura_richiesta.stat_costo_forgiatura.valore_base_predefinito
             if val > 0: costo_base = val
        
        costo_totale = infusione.livello * costo_base
        
        if crafter.crediti < costo_totale:
            raise ValidationError("Crediti insufficienti.")
        crafter.modifica_crediti(-costo_totale, f"Creazione {infusione.nome}")

        with transaction.atomic():
            nuovo_oggetto = Oggetto.objects.create(
                nome=infusione.nome,
                testo=infusione.testo,
                tipo_oggetto=tipo_output,
                infusione_generatrice=infusione,
                aura=infusione.aura_infusione, 
            )
            for stat_link in infusione.infusionestatisticabase_set.all():
                nuovo_oggetto.statistiche_base.add(
                    stat_link.statistica, 
                    through_defaults={'valore_base': stat_link.valore_base}
                )
            nuovo_oggetto.sposta_in_inventario(target) 
            
            if tipo_output in [TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE]:
                nuovo_oggetto.is_equipaggiato = True
                nuovo_oggetto.save()

        return nuovo_oggetto

    @staticmethod
    def assembla_mod(assemblatore: Personaggio, oggetto_host: Oggetto, mod: Oggetto):
        if oggetto_host.inventario_corrente != assemblatore or mod.inventario_corrente != assemblatore:
            raise ValidationError("Devi possedere entrambi gli oggetti.")
        
        classe = oggetto_host.classe_oggetto
        if not classe:
            raise ValidationError("L'oggetto ospite non ha una classe definita.")

        num_mod_attuali = oggetto_host.potenziamenti_installati.filter(tipo_oggetto=TIPO_OGGETTO_MOD).count()
        if mod.tipo_oggetto == TIPO_OGGETTO_MOD and num_mod_attuali >= classe.max_mod_totali:
             raise ValidationError("Slot Mod esauriti su questo oggetto.")
        
        with transaction.atomic():
            mod.ospitato_su = oggetto_host
            mod.sposta_in_inventario(None)
            mod.save()

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
        
        if not personaggio.infusioni_possedute.filter(pk=infusione_id).exists():
             raise ValidationError("Non conosci questa infusione.")

        costo_crediti, durata_secondi = GestioneCraftingService.calcola_costi_forgiatura(personaggio, infusione)
        
        if personaggio.crediti < costo_crediti:
            raise ValidationError(f"Crediti insufficienti. Richiesti: {costo_crediti}")

        with transaction.atomic():
            personaggio.modifica_crediti(-costo_crediti, f"Avvio forgiatura: {infusione.nome}")
            fine_prevista = timezone.now() + timedelta(seconds=durata_secondi)
            forgiatura = ForgiaturaInCorso.objects.create(personaggio=personaggio, infusione=infusione, data_fine_prevista=fine_prevista, slot_target=slot_target)
            
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

        from .services import crea_oggetto_da_infusione
        
        with transaction.atomic():
            nuovo_oggetto = crea_oggetto_da_infusione(task.infusione, personaggio)
            if task.slot_target:
                nuovo_oggetto.slot_corpo = task.slot_target
                nuovo_oggetto.is_equipaggiato = True
                nuovo_oggetto.save()
            task.delete()
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
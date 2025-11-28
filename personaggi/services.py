# personaggi/services.py

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    Oggetto, OggettoStatistica, 
    TIPO_OGGETTO_MOD, TIPO_OGGETTO_MATERIA, 
    TIPO_OGGETTO_FISICO, OggettoInInventario,
    STATISTICA  # Assumendo che STATISTICA sia importabile o usiamo stringhe
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
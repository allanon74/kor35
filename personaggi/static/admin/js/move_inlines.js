document.addEventListener("DOMContentLoaded", function() {
    const $ = django.jQuery;

    // Funzione helper per spostare l'inline dopo il fieldset
    function moveInline(inlineId, anchorClass) {
        // Trova il fieldset che ha la nostra classe specifica
        var fieldset = $('fieldset.' + anchorClass);
        // Trova il gruppo inline (Django assegna ID basati sul nome del modello M2M)
        // Nota: Gli ID sono tutti minuscoli
        var inlineGroup = $('#' + inlineId);

        if (fieldset.length && inlineGroup.length) {
            inlineGroup.insertAfter(fieldset);
        }
    }

    // Eseguiamo lo spostamento.
    // Gli ID degli inline group in Django sono tipicamente: #nometabella_set-group
    // Devono corrispondere ai nomi dei modelli definiti in models.py (minuscoli)
    
    // Sposta la tabella RequisitoDoppia sotto il fieldset Doppia Formula
    moveInline('modelloaurarequisitodoppia_set-group', 'anchor-doppia');

    // Sposta la tabella RequisitoCaratt sotto il fieldset Formula Caratteristica
    moveInline('modelloaurarequisitocaratt_set-group', 'anchor-caratt');
});
document.addEventListener("DOMContentLoaded", function() {
    
    function moveAndBindInline(inlineId, anchorClass) {
        // 1. Trova gli elementi usando Javascript puro
        // Nota: getElementsByClassName restituisce una lista, prendiamo il primo elemento [0]
        var fieldsets = document.getElementsByClassName(anchorClass);
        var inlineGroup = document.getElementById(inlineId);

        // Se uno dei due non esiste, ci fermiamo
        if (fieldsets.length === 0 || !inlineGroup) {
            console.warn('Elementi non trovati:', anchorClass, inlineId);
            return;
        }

        var fieldset = fieldsets[0];

        // 2. Aggiungi classe per il CSS e SPOSTA fisicamente l'elemento
        inlineGroup.classList.add('moved-inline');
        fieldset.appendChild(inlineGroup);

        // 3. Funzione per gestire la visibilità
        function updateVisibility() {
            if (fieldset.classList.contains('collapsed')) {
                inlineGroup.style.display = 'none';
            } else {
                inlineGroup.style.display = 'block';
            }
        }

        // Stato iniziale
        updateVisibility();

        // 4. Intercetta il click sul titolo per sincronizzare l'apertura
        // Cerca il link 'Show/Hide' o l'h2 che Django usa per il toggle
        var toggleBtn = fieldset.querySelector('h2');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', function() {
                // Un piccolo timeout è necessario per dare tempo a Django di cambiare la classe
                setTimeout(updateVisibility, 50);
            });
        }
    }

    // Eseguiamo lo spostamento per le due tabelle
    moveAndBindInline('req_doppia_rel-group', 'anchor-doppia');
    moveAndBindInline('req_caratt_rel-group', 'anchor-caratt');
});
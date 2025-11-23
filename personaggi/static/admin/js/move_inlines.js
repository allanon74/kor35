document.addEventListener("DOMContentLoaded", function() {
    const $ = django.jQuery;

    function moveAndBindInline(inlineId, anchorClass) {
        var fieldset = $('fieldset.' + anchorClass);
        // NOTA: Qui l'ID cambia perché nel models.py hai usato related_name
        var inlineGroup = $('#' + inlineId);

        if (fieldset.length && inlineGroup.length) {
            // 1. Spostamento
            inlineGroup.addClass('moved-inline');
            inlineGroup.appendTo(fieldset);

            // 2. Stato Iniziale
            if (fieldset.hasClass('collapsed')) {
                inlineGroup.hide();
            }

            // 3. Gestione Click Mostra/Nascondi
            fieldset.find('h2 .collapse-toggle').on('click', function(e) {
                setTimeout(function() {
                    if (fieldset.hasClass('collapsed')) {
                        inlineGroup.slideUp(200);
                    } else {
                        inlineGroup.slideDown(200);
                    }
                }, 50);
            });
        } else {
            console.warn("Impossibile trovare fieldset o inline:", anchorClass, inlineId);
        }
    }

    // USARE QUESTI NUOVI ID:
    // ID derivato da related_name='req_doppia_rel'
    moveAndBindInline('req_doppia_rel-group', 'anchor-doppia');
    
    // ID derivato da related_name='req_caratt_rel'
    moveAndBindInline('req_caratt_rel-group', 'anchor-caratt');
});
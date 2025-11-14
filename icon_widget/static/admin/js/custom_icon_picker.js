// Funzione per ottenere il CSRF token (necessaria per il POST)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');


window.initCustomIconPicker = function(options) {
    const input = document.getElementById(options.inputId);
    if (!input) return; // Se l'input non è trovato, esci
    
    // Evita di inizializzare due volte lo stesso campo
    if (input.dataset.iconPickerInitialized) return;
    input.dataset.iconPickerInitialized = true;

    const preview = document.getElementById(`icon_preview_${options.name}`);
    const resultsDiv = document.getElementById(`icon_results_${options.name}`);
    const statusSpan = document.getElementById(`icon_status_${options.name}`);
    const colorField = document.getElementById('id_colore'); // Come da tua richiesta

    function setupInitialIcon() {
        const value = input.value;
        if (value && value.endsWith('.svg')) {
            preview.src = `/media/${value}`;
            preview.style.display = 'inline-block';
        }
    }
    
    setupInitialIcon();

    let searchTimeout;
    input.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            const query = input.value;
            if (query.length < 3) {
                resultsDiv.innerHTML = '';
                return;
            }
            
            statusSpan.textContent = 'Ricerca...';
            try {
                const response = await fetch(`https://api.iconify.design/search?query=${encodeURIComponent(query)}&limit=10`);
                const data = await response.json();
                
                resultsDiv.innerHTML = '';
                if (data.icons.length > 0) {
                    data.icons.forEach(iconName => {
                        const item = document.createElement('div');
                        item.className = 'icon-dropdown-item';
                        // item.innerHTML = `<img src="https://api.iconify.design/${iconName}.svg" style="width: 16px; height: 16px; margin-right: 5px;"> <span>${iconName}</span>`;
                        // iconImg.src = `https://api.iconify.design/${iconName}.svg`;
                        // iconImg.className = "icon-preview"; // Usa la classe CSS
                        
                        // const iconText = document.createElement("span");
                        // iconText.textContent = iconName;
                        // iconText.className = "icon-name"; // Usa la classe CSS

                        // item.appendChild(iconImg);
                        // item.appendChild(iconText);

                        // item.style.padding = '5px';
                        // item.style.cursor = 'pointer';
                        
                        // item.addEventListener('click', () => selectIcon(iconName));
                        // resultsDiv.appendChild(item);

                        item.className = 'icon-dropdown-item';
                        item.innerHTML = `<img src="https://api.iconify.design/${iconName}.svg" class="icon-preview"> <span class="icon-name">${iconName}</span>`;
                        // --- FINE MODIFICA ---
                        
                        item.style.cursor = 'pointer'; // Lasciamo questo per sicurezza
                        
                        // Questo ora funzionerà di nuovo
                        item.addEventListener('click', () => selectIcon(iconName)); 
                        resultsDiv.appendChild(item);
                    });
                }
                statusSpan.textContent = '';
            } catch (e) {
                statusSpan.textContent = 'Errore ricerca.';
            }
        }, 300); // Debounce di 300ms
    });

    async function selectIcon(iconName) {
        const color = colorField ? colorField.value : '#000000';
        
        resultsDiv.innerHTML = ''; 
        statusSpan.textContent = `Salvataggio di ${iconName}...`;

        try {
            const formData = new FormData();
            formData.append('icon', iconName);
            formData.append('color', color);
            formData.append('model', options.modelName); // Usa il modelName dinamico

            const response = await fetch(`/icon-widget-api/save-icon/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken },
                body: formData
            });
            
            if (!response.ok) throw new Error(`Errore server: ${response.status}`);
            
            const data = await response.json(); // { "path": "...", "url": "..." }
            
            input.value = data.path; 
            preview.src = data.url;
            preview.style.display = 'inline-block';
            statusSpan.textContent = 'Icona salvata!';

        } catch (e) {
            console.error('Salvataggio icona fallito:', e);
            statusSpan.textContent = 'Salvataggio fallito.';
            input.value = iconName; 
        }
    }
};
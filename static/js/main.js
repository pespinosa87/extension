document.addEventListener('DOMContentLoaded', function() {
    // Escaneo manual
    const btnEscaneoManual = document.getElementById('btnEscaneoManual');
    if (btnEscaneoManual) {
        btnEscaneoManual.addEventListener('click', function() {
            this.disabled = true;
            this.textContent = 'Escaneando...';
            
            fetch('/api/iniciar-escaneo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                alert('Escaneo completado: ' + data.mensaje);
                location.reload();
            })
            .catch(error => {
                alert('Error durante el escaneo: ' + error);
            })
            .finally(() => {
                this.disabled = false;
                this.textContent = 'Iniciar escaneo manual';
            });
        });
    }
    
    // Auto-refresh
    setTimeout(() => {
        window.location.reload();
    }, 5 * 60 * 1000); // Recargar cada 5 minutos
});
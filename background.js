// Ejecutar una comprobación periódica cada 30 minutos
const INTERVALO_ACTUALIZACION = 30 * 60 * 1000; // 30 minutos en milisegundos

// Variable para almacenar el ID del temporizador
let timerID = null;

// Función para realizar la actualización en segundo plano
async function actualizarDatos() {
  try {
    // Obtener la URL de la API desde el almacenamiento
    const data = await chrome.storage.local.get('apiUrl');
    const apiUrl = data.apiUrl;
    
    if (!apiUrl) {
      console.log('URL de API no configurada');
      return;
    }
    
    console.log('Actualizando datos en segundo plano...');
    
    // Obtener temas actualizados
    const response = await fetch(`${apiUrl}/temas`);
    const temas = await response.json();
    
    // Contar temas por estado
    const conteo = {
      rojo: 0,
      amarillo: 0,
      verde: 0,
      total: temas.length
    };
    
    temas.forEach(tema => {
      conteo[tema.estado]++;
    });
    
    // Actualizar la insignia con el número de temas en rojo
    if (conteo.rojo > 0) {
      chrome.action.setBadgeBackgroundColor({ color: '#f44336' });
      chrome.action.setBadgeText({ text: conteo.rojo.toString() });
    } else if (conteo.amarillo > 0) {
      chrome.action.setBadgeBackgroundColor({ color: '#ffc107' });
      chrome.action.setBadgeText({ text: conteo.amarillo.toString() });
    } else {
      chrome.action.setBadgeText({ text: '' });
    }
    
    // Guardar conteo para referencia rápida
    chrome.storage.local.set({ conteoTemas: conteo });
    
    console.log('Actualización en segundo plano completada');
  } catch (error) {
    console.error('Error en la actualización en segundo plano:', error);
  }
}

// Función para iniciar las actualizaciones periódicas
function iniciarActualizacionesPeriodicas() {
  // Limpiar cualquier temporizador existente
  if (timerID) {
    clearInterval(timerID);
  }
  
  // Realizar una actualización inmediata
  actualizarDatos();
  
  // Configurar actualizaciones periódicas
  timerID = setInterval(actualizarDatos, INTERVALO_ACTUALIZACION);
  console.log('Iniciadas actualizaciones periódicas');
}

// Escuchar cambios en la configuración
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.apiUrl) {
    console.log('Detectado cambio en la URL de la API');
    iniciarActualizacionesPeriodicas();
  }
});

// Iniciar cuando la extensión se carga
chrome.runtime.onStartup.addListener(() => {
  iniciarActualizacionesPeriodicas();
});

// Iniciar cuando la extensión se instala o actualiza
chrome.runtime.onInstalled.addListener(() => {
  iniciarActualizacionesPeriodicas();
});

// Escuchar mensajes desde popup.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'actualizarDatos') {
    actualizarDatos().then(() => {
      sendResponse({ success: true });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    
    // Indicar que se enviará una respuesta asíncrona
    return true;
  }
});
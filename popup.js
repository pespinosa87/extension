document.addEventListener('DOMContentLoaded', function() {
    // Variables globales
    let apiUrl = '';
    
    // Cargar configuración guardada
    chrome.storage.local.get('apiUrl', function(data) {
      if (data.apiUrl) {
        apiUrl = data.apiUrl;
        document.getElementById('apiUrl').value = apiUrl;
        cargarDatos();
      }
    });
    
    // Cambiar entre pestañas
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
      tab.addEventListener('click', function() {
        const tabName = this.getAttribute('data-tab');
        
        // Activar pestaña seleccionada
        tabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        
        // Mostrar contenido correspondiente
        tabContents.forEach(content => {
          content.style.display = 'none';
        });
        document.getElementById(`${tabName}Content`).style.display = 'block';
      });
    });
    
    // Botón de actualizar
    document.getElementById('refreshButton').addEventListener('click', function() {
      cargarDatos();
    });
    
    // Guardar URL de la API
    document.getElementById('apiUrl').addEventListener('change', function() {
      apiUrl = this.value.trim();
      chrome.storage.local.set({ apiUrl: apiUrl }, function() {
        console.log('API URL guardada');
        cargarDatos();
      });
    });
    
    // Agregar nuevo medio
    document.getElementById('agregarMedio').addEventListener('click', function() {
      const nombre = document.getElementById('medioNombre').value.trim();
      const url = document.getElementById('medioUrl').value.trim();
      const tipo = document.getElementById('medioTipo').value;
      const resultadoDiv = document.getElementById('resultadoAgregar');
      
      if (!nombre || !url) {
        resultadoDiv.innerHTML = '<p style="color: red;">Por favor, completa todos los campos</p>';
        return;
      }
      
      if (!apiUrl) {
        resultadoDiv.innerHTML = '<p style="color: red;">Por favor, configura primero la URL de la API</p>';
        return;
      }
      
      resultadoDiv.innerHTML = '<div class="loader"></div>';
      
      fetch(`${apiUrl}/medios`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ nombre, url, tipo })
      })
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          resultadoDiv.innerHTML = `<p style="color: red;">${data.error}</p>`;
        } else {
          resultadoDiv.innerHTML = `<p style="color: green;">Medio agregado correctamente (ID: ${data.id})</p>`;
          document.getElementById('medioNombre').value = '';
          document.getElementById('medioUrl').value = '';
          cargarDatos();
        }
      })
      .catch(error => {
        console.error('Error:', error);
        resultadoDiv.innerHTML = '<p style="color: red;">Error al conectar con la API</p>';
      });
    });
    
    // Escaneo manual
    document.getElementById('escaneoManual').addEventListener('click', function() {
      const resultadoDiv = document.getElementById('resultadoEscaneo');
      
      if (!apiUrl) {
        resultadoDiv.innerHTML = '<p style="color: red;">Por favor, configura primero la URL de la API</p>';
        return;
      }
      
      resultadoDiv.innerHTML = '<div class="loader"></div>';
      
      fetch(`${apiUrl}/iniciar-escaneo`, {
        method: 'POST'
      })
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          resultadoDiv.innerHTML = `<p style="color: red;">${data.error}</p>`;
        } else {
          resultadoDiv.innerHTML = `<p style="color: green;">${data.mensaje}</p>`;
          setTimeout(() => {
            cargarDatos();
          }, 3000);
        }
      })
      .catch(error => {
        console.error('Error:', error);
        resultadoDiv.innerHTML = '<p style="color: red;">Error al conectar con la API</p>';
      });
    });
    
    // Función para cargar datos
    function cargarDatos() {
      if (!apiUrl) return;
      
      cargarTablaTemas('propios', 'propiosTable');
      cargarTablaTemas('competencia', 'competenciaTable');
      cargarTablaTemas('todos', 'todosTable');
    }
    
    // Función para cargar tabla de temas según tipo
    function cargarTablaTemas(tipo, contenedorId) {
      const contenedor = document.getElementById(contenedorId);
      contenedor.innerHTML = '<div class="loader"></div>';
      
      const endpoint = tipo === 'todos' ? `${apiUrl}/temas` : `${apiUrl}/temas?tipo=${tipo}`;
      
      fetch(endpoint)
        .then(response => response.json())
        .then(temas => {
          if (temas.length === 0) {
            contenedor.innerHTML = '<p>No hay temas disponibles para mostrar</p>';
            return;
          }
          
          // Ordenar temas por estado (rojo primero, luego amarillo, luego verde)
          temas.sort((a, b) => {
            const orden = { "rojo": 0, "amarillo": 1, "verde": 2 };
            return orden[a.estado] - orden[b.estado];
          });
          
          // Crear tabla
          let html = `
            <table>
              <thead>
                <tr>
                  <th>Tema</th>
                  <th>Medio</th>
                  <th>Estado</th>
                  <th>Tiempo</th>
                  <th>Última Vez</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
          `;
          
          temas.forEach(tema => {
            const fechaUltimaVez = new Date(tema.ultima_vez).toLocaleString();
            
            html += `
              <tr>
                <td>${tema.nombre}</td>
                <td>${tema.medio}</td>
                <td><span class="tag ${tema.estado}">${tema.estado.toUpperCase()}</span></td>
                <td>${tema.duracion_horas.toFixed(1)} horas</td>
                <td>${fechaUltimaVez}</td>
                <td>
                  <a href="${tema.url}" target="_blank">Ver noticia</a>
                </td>
              </tr>
            `;
          });
          
          html += `
              </tbody>
            </table>
          `;
          
          contenedor.innerHTML = html;
        })
        .catch(error => {
          console.error('Error:', error);
          contenedor.innerHTML = '<p class="error">Error al cargar los datos. Verifica la URL de la API.</p>';
        });
    }
  });
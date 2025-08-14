const baseUrl = ''; // Usa rutas relativas, porque frontend y backend están juntos


// variables de estado de edición globales (puede ponerse arriba)
let creditoEditId = null;
let planillaEditId = null;

// ---------- Simulador de crédito ----------
async function initSimuladorCredito() {
  const form = document.getElementById('form-credito');
  const resultadoCard = document.getElementById('resultado');
  const detalle = document.getElementById('detalle-credito');
  const submitBtn = form.querySelector('button[type="submit"]');

  form?.addEventListener('submit', async e => {
    e.preventDefault();
    submitBtn.disabled = true;
    submitBtn.textContent = creditoEditId ? 'Guardando cambios...' : 'Guardando...';
    detalle.innerHTML = '';

    const data = Object.fromEntries(new FormData(form).entries());
    data.edad = parseInt(data.edad);
    data.ingresos_mensuales = parseFloat(data.ingresos_mensuales);
    data.gastos_mensuales = parseFloat(data.gastos_mensuales);
    data.valor_patrimonio = parseFloat(data.valor_patrimonio);
    data.numero_empleados = parseInt(data.numero_empleados || 0);

    try {
      let res;
      if (creditoEditId) {
        // modo edición
        res = await fetch(`${baseUrl}/api/credito/${creditoEditId}`, {
          method: 'PUT',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(data)
        });
      } else {
        // modo creación
        res = await fetch(`${baseUrl}/api/credito`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(data)
        });
      }

      const json = await res.json();

      if (!res.ok) {
        mostrarAlert(detalle, json.error || 'Error en la simulación', 'error');
        resultadoCard.style.display = 'block';
        return;
      }

      resultadoCard.style.display = 'none';
      detalle.innerHTML = `
        Señor/a ${json.nombres} ${json.apellidos} su registrose a guardado con éxito
		su valor aprobado de crédito es aproximadamente:${json.valor_aprobado ?? 'N/A'}
      `;

      // Reiniciar formulario y estado
      form.reset();
      creditoEditId = null;
      submitBtn.textContent = 'Calcular crédito';
      form.querySelectorAll('input').forEach(i => i.classList.remove('is-invalid'));
      const firstInput = form.querySelector('input[name="nombres"]');
      if (firstInput) firstInput.focus();

      // (Opcional) si tienes botón de cancelar edición puedes ocultarlo aquí

    } catch (err) {
      console.error(err);
      mostrarAlert(detalle, 'Fallo de red', 'error');
      resultadoCard.style.display = 'block';
    } finally {
      submitBtn.disabled = false;
    }
  });

  document.getElementById('btn-buscar')?.addEventListener('click', async () => {
    const cedula = document.getElementById('buscar-cedula').value.trim();
    const cont = document.getElementById('historial-credito');
    if (!cedula) return;
    cont.innerHTML = 'Cargando...';
    try {
      const res = await fetch(`${baseUrl}/api/credito?cedula=${encodeURIComponent(cedula)}`);
      const lista = await res.json();
      if (!res.ok) {
        cont.innerHTML = `<div class="alert alert-error">${lista.error || 'Error al buscar'}</div>`;
        return;
      }
      if (lista.length === 0) {
        cont.innerHTML = `<div class="small">No hay registros para ${cedula}</div>`;
        return;
      }
      let html = '<table class="table"><thead><tr><th>Fecha</th><th>Documento</th><th>Valor aprobado</th><th>Acciones</th></tr></thead><tbody>';
      lista.forEach(item => {
        html += `<tr>
          <td>${new Date(item.created_at).toLocaleDateString()}</td>
          <td>${item.documento_identidad}</td>
          <td>${item.valor_aprobado ?? ''}</td>
          <td>
            <button data-item='${encodeURIComponent(JSON.stringify(item))}' onclick="editarCredito(this)" class="button" style="padding:4px 8px;font-size:.75rem;">Editar</button>
            <button onclick="eliminarCredito(${item.id})" style="margin-left:4px;padding:4px 8px;font-size:.75rem;background:#e05656;color:white;border:none;border-radius:4px;cursor:pointer;">Eliminar</button>
          </td>
        </tr>`;
      });
      html += '</tbody></table>';
      cont.innerHTML = html;
    } catch (err) {
      cont.innerHTML = `<div class="alert alert-error">Error de red</div>`;
    }
  });
}

function editarCredito(button) {
  // extrae el item embebido en data-item
  try {
    const raw = decodeURIComponent(button.getAttribute('data-item'));
    const item = JSON.parse(raw);

    const form = document.getElementById('form-credito');
    form.querySelector('input[name="nombres"]').value = item.nombres || '';
    form.querySelector('input[name="apellidos"]').value = item.apellidos || '';
    form.querySelector('input[name="documento_identidad"]').value = item.documento_identidad || '';
    form.querySelector('input[name="edad"]').value = item.edad ?? '';
    form.querySelector('input[name="fecha_nacimiento"]').value = item.fecha_nacimiento ? item.fecha_nacimiento.split('T')[0] : '';
    form.querySelector('input[name="ingresos_mensuales"]').value = item.ingresos_mensuales ?? '';
    form.querySelector('input[name="gastos_mensuales"]').value = item.gastos_mensuales ?? '';
    form.querySelector('input[name="valor_patrimonio"]').value = item.valor_patrimonio ?? '';
    form.querySelector('input[name="dimension_terreno"]').value = item.dimension_terreno || '';
    form.querySelector('input[name="destinacion_credito"]').value = item.destinacion_credito || '';
    form.querySelector('input[name="numero_empleados"]').value = item.numero_empleados ?? '';

    // marcar modo edición
    creditoEditId = item.id;
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.textContent = 'Guardar cambios';
    form.querySelector('input[name="nombres"]').focus();
  } catch (e) {
    console.error('Error al cargar para edición:', e);
    alert('No se pudo cargar el registro para editar.');
  }
}

// ---------- Planilla financiera ----------
async function initPlanilla() {
  const form = document.getElementById('form-planilla');
  const resultadoCard = document.getElementById('resultado-planilla');
  const detalle = document.getElementById('detalle-planilla');
  const submitBtn = form.querySelector('button[type="submit"]');

  form?.addEventListener('submit', async e => {
    e.preventDefault();
    submitBtn.disabled = true;
    submitBtn.textContent = planillaEditId ? 'Guardando cambios...' : 'Guardando...';
    detalle.innerHTML = '';

    const data = Object.fromEntries(new FormData(form).entries());
    data.ingresos = parseFloat(data.ingresos);
    data.gastos = parseFloat(data.gastos);
    data.inversiones = parseFloat(data.inversiones);

    try {
      let res;
      if (planillaEditId) {
        res = await fetch(`${baseUrl}/api/planilla/${planillaEditId}`, {
          method: 'PUT',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(data)
        });
      } else {
        res = await fetch(`${baseUrl}/api/planilla`, {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(data)
        });
      }
      const json = await res.json();
      if (!res.ok) {
        mostrarAlert(detalle, json.error || 'Error creando/actualizando planilla', 'error');
        resultadoCard.style.display = 'block';
        return;
      }
      resultadoCard.style.display = 'block';
      detalle.innerHTML = `
        <p><strong>Cédula:</strong> ${json.cedula}</p>
        <p><strong>Ingresos:</strong> ${json.ingresos}</p>
        <p><strong>Gastos:</strong> ${json.gastos}</p>
        <p><strong>Inversiones:</strong> ${json.inversiones}</p>
        <p><strong>Utilidad:</strong> ${json.utilidad}</p>
        <p><strong>Observaciones:</strong> ${json.observaciones}</p>
      `;
      // reiniciar y estado
      form.reset();
      planillaEditId = null;
      const firstInput = form.querySelector('input[name="cedula"]');
      if (firstInput) firstInput.focus();
      submitBtn.textContent = 'Guardar registro';
    } catch (err) {
      console.error(err);
      mostrarAlert(detalle, 'Fallo de red', 'error');
      resultadoCard.style.display = 'block';
    } finally {
      submitBtn.disabled = false;
    }
  });

  document.getElementById('btn-buscar-planilla')?.addEventListener('click', async () => {
    const cedula = document.getElementById('buscar-cedula-planilla').value.trim();
    const cont = document.getElementById('historial-planilla');
    if (!cedula) return;
    cont.innerHTML = 'Cargando...';
    try {
      const res = await fetch(`${baseUrl}/api/planilla?cedula=${encodeURIComponent(cedula)}`);
      const lista = await res.json();
      if (!res.ok) {
        cont.innerHTML = `<div class="alert alert-error">${lista.error || 'Error'}</div>`;
        return;
      }
      if (lista.length === 0) {
        cont.innerHTML = `<div class="small">No hay registros para ${cedula}</div>`;
        return;
      }
      let html = '<table class="table"><thead><tr><th>Fecha</th><th>Ingresos</th><th>Gastos</th><th>Inversiones</th><th>Utilidad</th><th>Acciones</th></tr></thead><tbody>';
      lista.forEach(i => {
        html += `<tr>
          <td>${new Date(i.fecha).toLocaleDateString()}</td>
          <td>${i.ingresos}</td>
          <td>${i.gastos}</td>
          <td>${i.inversiones}</td>
          <td>${i.utilidad}</td>
          <td>
            <button data-item='${encodeURIComponent(JSON.stringify(i))}' onclick="editarPlanilla(this)" class="button" style="padding:4px 8px;font-size:.75rem;">Editar</button>
            <button onclick="eliminarPlanilla(${i.id})" style="margin-left:4px;padding:4px 8px;font-size:.75rem;background:#e05656;color:white;border:none;border-radius:4px;cursor:pointer;">Eliminar</button>
          </td>
        </tr>`;
      });
      html += '</tbody></table>';
      cont.innerHTML = html;
    } catch (e) {
      cont.innerHTML = `<div class="alert alert-error">Error de red</div>`;
    }
  });
}

window.eliminarCredito = async function(sim_id) {
  if (!confirm('¿Seguro que quieres eliminar este crédito?')) return;

  try {
    const res = await fetch(`${baseUrl}/api/credito/${sim_id}`, {
      method: 'DELETE'
    });
    const data = await res.json();

    if (!res.ok) {
      alert(data.error || 'Error al eliminar');
      return;
    }

    alert('Crédito eliminado correctamente');
    document.getElementById('btn-buscar').click();
  } catch (err) {
    alert('Error de red al intentar eliminar');
  }
};

function editarPlanilla(button) {
  try {
    const raw = decodeURIComponent(button.getAttribute('data-item'));
    const item = JSON.parse(raw);

    const form = document.getElementById('form-planilla');
    form.querySelector('input[name="cedula"]').value = item.cedula || '';
    form.querySelector('input[name="ingresos"]').value = item.ingresos ?? '';
    form.querySelector('input[name="gastos"]').value = item.gastos ?? '';
    form.querySelector('input[name="inversiones"]').value = item.inversiones ?? '';
    form.querySelector('textarea[name="observaciones"]').value = item.observaciones || '';

    planillaEditId = item.id;
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.textContent = 'Guardar cambios';
    form.querySelector('input[name="cedula"]').focus();
  } catch (e) {
    console.error('Error al cargar planilla para edición:', e);
    alert('No se pudo cargar la planilla para editar.');
  }

}

//botones de alertas
//alerta boton credito
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('form-credito');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const data = Object.fromEntries(new FormData(form).entries());

        try {
            const res = await fetch('/api/credito', {
                method: 'POST', // si usas PUT para editar, cámbialo dinámicamente
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const json = await res.json();

            if (res.ok) {
                Swal.fire({
                    title: '¡Simulacion de Crédito registrado!',
                    text: 'La simulación de solicitud de crédito se ha guardado exitosamente.',
                    imageUrl: 'static/img/logo_completo.png', 
                    imageWidth: 220,
                    imageHeight: 200,
                    imageAlt: 'Logo2',
                    confirmButtonColor: '#73CBD8',
                    icon: 'success'
                });

                form.reset();
            } else {
                Swal.fire('Error', json.error || 'No se pudo guardar el crédito', 'error');
            }

        } catch (error) {
            console.error(error);
            Swal.fire('Error', 'Hubo un problema al conectar con el servidor', 'error');
        }
    });
});

// alerta boton planilla
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('form-planilla');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const data = Object.fromEntries(new FormData(form).entries());

        try {
            const res = await fetch('/api/planilla', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const json = await res.json();

            if (res.ok) {
                Swal.fire({
                    title: '¡Registro guardado!',
                    text: 'La planilla se ha guardado correctamente.',
                    imageUrl: 'static/img/logo_completo.png', 
                    imageWidth: 220,
                    imageHeight: 200,
                    imageAlt: 'Logo2',
                    confirmButtonColor: '#73CBD8',
                    icon: 'success'
                });

                form.reset();
            } else {
                Swal.fire('Error', json.error || 'No se pudo guardar la planilla', 'error');
            }

        } catch (error) {
            console.error(error);
            Swal.fire('Error', 'Hubo un problema al conectar con el servidor', 'error');
        }
    });
});


document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('form-contacto');

    form.addEventListener('submit', async (e) => {
        e.preventDefault(); // Evita recarga de página

        // Capturamos datos del formulario
        const data = Object.fromEntries(new FormData(form).entries());

        try {
            // Enviar datos al backend
            const res = await fetch('/api/contacto', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const json = await res.json();

            // Si el backend responde OK 
            if (res.ok) {
                // Mostrar SweetAlert después de guardar
                Swal.fire({
                    title: '¡Gracias por tu preferencia!',
                    text: 'Gracias por enviar sus datos, un agente se contactara lo mas pronto posible.',
                    imageUrl: 'static/img/logo_completo.png',
                    imageWidth: 220,
                    imageHeight: 200,
                    imageAlt: 'Logo2',
                    confirmButtonColor: '#73CBD8',
                });

                form.reset(); // limpiar el formulario
            } else {
                Swal.fire('Error', json.error || 'No se pudo guardar el contacto', 'error');
            }

        } catch (error) {
            console.error(error);
            Swal.fire('Error', 'Hubo un problema al conectar con el servidor', 'error');
        }
    });
});


 document.addEventListener('DOMContentLoaded', () => {
  initSimuladorCredito();
  initPlanilla(); // si también estás usando planilla
});
(function () {
  // Decentral ERD Explorer - Interactive & Responsive Canvas
  var state = {
    catalog: null,
    erd: null,
    selectedEntityId: null,
    zoom: 1,
    panX: 40,
    panY: 40,
    isPanning: false,
    startPanMouseX: 0,
    startPanMouseY: 0,
    draggingCard: null,
    cardDragStartX: 0,
    cardDragStartY: 0,
    cardPositions: {}, // { entityId: { x, y } }
    filterSchema: '',
    filterKind: '',
    filterQuery: ''
  };

  // DOM Elements
  var snapshotEl = document.getElementById('snapshot');
  var coverageBannerEl = document.getElementById('coverage-banner');
  var schemaFilterEl = document.getElementById('schema-filter');
  var kindFilterEl = document.getElementById('kind-filter');
  var searchInput = document.getElementById('search');
  var entitiesListEl = document.getElementById('entities');
  var entitiesCountEl = document.getElementById('entities-count');
  var entityTemplate = document.getElementById('entity-template');

  var canvasContainer = document.getElementById('erd-canvas-container');
  var viewportEl = document.getElementById('erd-viewport');
  var svgLayer = document.getElementById('erd-svg-layer');
  var cardsLayer = document.getElementById('erd-cards-layer');
  var zoomIndicator = document.getElementById('zoom-indicator');

  var btnZoomIn = document.getElementById('btn-zoom-in');
  var btnZoomOut = document.getElementById('btn-zoom-out');
  var btnZoomReset = document.getElementById('btn-zoom-reset');
  var btnLayout = document.getElementById('btn-layout');

  var inspectorPanel = document.getElementById('inspector-panel');
  var inspectorTitle = document.getElementById('inspector-title');
  var inspectorContent = document.getElementById('inspector-content');
  var inspectorDiagram = document.getElementById('diagram');
  var btnCloseInspector = document.getElementById('btn-close-inspector');

  function api(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('API request failed: ' + r.statusText);
      return r.json();
    });
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    var div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  }

  // Viewport transforms (Zoom & Pan)
  function updateViewportTransform() {
    viewportEl.style.transform = 'translate(' + state.panX + 'px, ' + state.panY + 'px) scale(' + state.zoom + ')';
    zoomIndicator.textContent = Math.round(state.zoom * 100) + '%';
  }

  function setZoom(newZoom, centerX, centerY) {
    var minZoom = 0.3;
    var maxZoom = 2.5;
    var clamped = Math.max(minZoom, Math.min(maxZoom, newZoom));
    if (centerX !== undefined && centerY !== undefined) {
      var factor = clamped / state.zoom;
      state.panX = centerX - (centerX - state.panX) * factor;
      state.panY = centerY - (centerY - state.panY) * factor;
    }
    state.zoom = clamped;
    updateViewportTransform();
  }

  // Load catalog and initial ERD
  function init() {
    api('/api/catalog').then(function (meta) {
      state.catalog = meta;
      snapshotEl.textContent = (meta.package_id || meta.snapshot_id) + ' · ' + meta.source;
      if (meta.coverage && meta.coverage.foreign_keys_external_targets) {
        var ext = meta.coverage.foreign_keys_external_targets;
        coverageBannerEl.textContent = 'Cobertura FK externa parcial: ' + ext.rows + ' relaciones pendientes de lote.';
        coverageBannerEl.classList.remove('hidden');
      }
    }).catch(function (err) {
      snapshotEl.textContent = 'Error cargando metadatos';
    });

    loadErd();
    bindEvents();
  }

  function loadErd() {
    var queryParams = [];
    if (state.filterSchema) queryParams.push('schema=' + encodeURIComponent(state.filterSchema));
    if (state.filterQuery) queryParams.push('query=' + encodeURIComponent(state.filterQuery));
    var url = '/api/erd' + (queryParams.length ? '?' + queryParams.join('&') : '');

    api(url).then(function (erd) {
      state.erd = erd;
      populateSchemaOptions(erd.schemas);
      computeInitialLayout(erd.nodes);
      renderAll();
    }).catch(function (err) {
      console.error('Error loading ERD graph:', err);
    });
  }

  function populateSchemaOptions(schemas) {
    var current = schemaFilterEl.value;
    schemaFilterEl.innerHTML = '<option value="">(Todos los esquemas)</option>';
    schemas.forEach(function (s) {
      var opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      if (s === current) opt.selected = true;
      schemaFilterEl.appendChild(opt);
    });
  }

  function computeInitialLayout(nodes, forceReset) {
    var cols = 3;
    var cardW = 270;
    var cardH = 220;
    var startX = 60;
    var startY = 60;

    nodes.forEach(function (n, idx) {
      if (!state.cardPositions[n.id] || forceReset) {
        var col = idx % cols;
        var row = Math.floor(idx / cols);
        state.cardPositions[n.id] = {
          x: startX + col * (cardW + 50),
          y: startY + row * (cardH + 40)
        };
      }
    });
  }

  function renderAll() {
    renderEntityList();
    renderCards();
    renderEdges();
  }

  function isVisibleNode(node) {
    if (state.filterSchema && node.schema !== state.filterSchema) return false;
    if (state.filterKind && node.kind !== state.filterKind) return false;
    if (state.filterQuery && !node.matches) return false;
    return true;
  }

  // Sidebar List
  function renderEntityList() {
    if (!state.erd) return;
    entitiesListEl.innerHTML = '';
    var visibleCount = 0;

    state.erd.nodes.forEach(function (node) {
      if (!isVisibleNode(node)) return;
      visibleCount++;

      var tpl = entityTemplate.content.cloneNode(true);
      var btn = tpl.querySelector('.entity-item-btn');
      var badge = tpl.querySelector('.entity-kind-badge');
      var label = tpl.querySelector('.entity-label-text');

      badge.textContent = node.kind === 'view' ? 'V' : 'T';
      badge.className = 'entity-kind-badge ' + node.kind;
      label.textContent = (node.schema ? node.schema + '.' : '') + node.name;

      if (node.id === state.selectedEntityId) {
        btn.classList.add('selected');
      }

      btn.onclick = function () {
        selectEntity(node.id);
        focusCard(node.id);
      };

      entitiesListEl.appendChild(tpl);
    });

    entitiesCountEl.textContent = visibleCount;
  }

  // Cards Layer
  function renderCards() {
    if (!state.erd) return;
    cardsLayer.innerHTML = '';

    state.erd.nodes.forEach(function (node) {
      var isVisible = isVisibleNode(node);
      var card = document.createElement('div');
      card.className = 'erd-card ' + node.kind;
      card.id = 'erd-card-' + node.id.replace(/[^a-zA-Z0-9_-]/g, '_');
      card.setAttribute('data-id', node.id);

      if (!isVisible) {
        card.style.display = 'none';
      }

      if (node.id === state.selectedEntityId) {
        card.classList.add('selected');
      }

      var pos = state.cardPositions[node.id] || { x: 50, y: 50 };
      card.style.left = pos.x + 'px';
      card.style.top = pos.y + 'px';

      // Header
      var header = document.createElement('div');
      header.className = 'erd-card-header';
      header.innerHTML =
        '<div class="card-title-group">' +
          '<span class="card-schema-tag">' + escapeHtml(node.schema) + '</span>' +
          '<span class="card-relation-name" title="' + escapeHtml(node.name) + '">' + escapeHtml(node.name) + '</span>' +
        '</div>' +
        '<span class="card-kind-tag">' + (node.kind === 'view' ? 'vista' : 'tabla') + '</span>';

      // Columns list
      var body = document.createElement('div');
      body.className = 'erd-card-body';

      var pkCols = {};
      var fkCols = {};
      if (node.columns) {
        node.columns.forEach(function (c) {
          if (c.key === 'primary') pkCols[c.name] = true;
          if (c.key === 'foreign') fkCols[c.name] = true;
        });
      }

      var colsHtml = '';
      if (node.columns && node.columns.length) {
        node.columns.forEach(function (c) {
          var isPk = !!pkCols[c.name];
          var isFk = !!fkCols[c.name];
          var rowClass = 'erd-col-row' + (isPk ? ' is-pk' : (isFk ? ' is-fk' : ''));
          var keyBadge = '';
          if (isPk) keyBadge = '<span class="key-icon pk">PK</span>';
          else if (isFk) keyBadge = '<span class="key-icon fk">FK</span>';

          colsHtml +=
            '<div class="' + rowClass + '">' +
              '<div class="col-name-group">' +
                keyBadge +
                '<span class="col-name" title="' + escapeHtml(c.name + ' - ' + (c.description || '')) + '">' + escapeHtml(c.name) + '</span>' +
              '</div>' +
              '<span class="col-type">' + escapeHtml(c.type) + '</span>' +
            '</div>';
        });
      } else {
        colsHtml = '<div class="erd-col-row placeholder-text">Sin columnas reportadas</div>';
      }
      body.innerHTML = colsHtml;

      // Footer
      var footer = document.createElement('div');
      footer.className = 'erd-card-footer';
      var colCount = (node.columns || []).length;
      footer.innerHTML =
        '<span>' + colCount + ' columna' + (colCount === 1 ? '' : 's') + '</span>' +
        '<span class="badge status-' + escapeHtml(node.provenance.status || 'declarada') + '">' + escapeHtml(node.provenance.status || '') + '</span>';

      card.appendChild(header);
      card.appendChild(body);
      card.appendChild(footer);

      // Card Events: Select & Drag
      card.addEventListener('mousedown', function (e) {
        e.stopPropagation();
        selectEntity(node.id);
        startDraggingCard(node.id, e);
      });

      cardsLayer.appendChild(card);
    });
  }

  // Edges SVG Layer
  function renderEdges() {
    if (!state.erd) return;
    svgLayer.innerHTML = '';

    // Define marker arrowhead
    var defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML =
      '<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">' +
        '<path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />' +
      '</marker>' +
      '<marker id="arrow-selected" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">' +
        '<path d="M 0 1 L 10 5 L 0 9 z" fill="#2563eb" />' +
      '</marker>' +
      '<marker id="arrow-composite" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">' +
        '<path d="M 0 1 L 10 5 L 0 9 z" fill="#7c3aed" />' +
      '</marker>';
    svgLayer.appendChild(defs);

    var cardW = 250;
    var nodeLookup = {};
    state.erd.nodes.forEach(function (n) { nodeLookup[n.id] = n; });

    state.erd.edges.forEach(function (edge) {
      var sourceNode = nodeLookup[edge.from_entity];
      var targetNode = nodeLookup[edge.to_entity];

      if (!sourceNode || !targetNode) return;
      if (!isVisibleNode(sourceNode) || !isVisibleNode(targetNode)) return;

      var srcPos = state.cardPositions[edge.from_entity] || { x: 50, y: 50 };
      var tgtPos = state.cardPositions[edge.to_entity] || { x: 350, y: 50 };

      var isHighlighted = (state.selectedEntityId === edge.from_entity || state.selectedEntityId === edge.to_entity);

      // Self reference loop
      if (edge.from_entity === edge.to_entity) {
        var loopPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        var sx = srcPos.x + cardW;
        var sy = srcPos.y + 40;
        var d = 'M ' + sx + ' ' + sy +
                ' C ' + (sx + 50) + ' ' + (sy - 30) + ', ' + (sx + 50) + ' ' + (sy + 70) + ', ' + sx + ' ' + (sy + 40);
        loopPath.setAttribute('d', d);
        var cls = 'erd-edge-path';
        if (edge.is_composite) cls += ' composite';
        if (isHighlighted) cls += ' highlighted';
        loopPath.setAttribute('class', cls);
        loopPath.setAttribute('marker-end', isHighlighted ? 'url(#arrow-selected)' : (edge.is_composite ? 'url(#arrow-composite)' : 'url(#arrow)'));
        svgLayer.appendChild(loopPath);
        return;
      }

      // Bezier connector between cards
      var startX, startY, endX, endY;
      if (srcPos.x + cardW < tgtPos.x) {
        // Source is to the left of target
        startX = srcPos.x + cardW;
        startY = srcPos.y + 50;
        endX = tgtPos.x;
        endY = tgtPos.y + 50;
      } else if (tgtPos.x + cardW < srcPos.x) {
        // Target is to the left of source
        startX = srcPos.x;
        startY = srcPos.y + 50;
        endX = tgtPos.x + cardW;
        endY = tgtPos.y + 50;
      } else {
        // Vertical arrangement
        startX = srcPos.x + cardW / 2;
        startY = srcPos.y < tgtPos.y ? srcPos.y + 120 : srcPos.y;
        endX = tgtPos.x + cardW / 2;
        endY = srcPos.y < tgtPos.y ? tgtPos.y : tgtPos.y + 120;
      }

      var dx = Math.abs(endX - startX) * 0.5;
      var pathD = 'M ' + startX + ' ' + startY +
                  ' C ' + (startX + (endX > startX ? dx : -dx)) + ' ' + startY + ', ' +
                  (endX - (endX > startX ? dx : -dx)) + ' ' + endY + ', ' +
                  endX + ' ' + endY;

      var edgePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      edgePath.setAttribute('d', pathD);
      var edgeClass = 'erd-edge-path';
      if (edge.is_composite) edgeClass += ' composite';
      if (isHighlighted) edgeClass += ' highlighted';
      edgePath.setAttribute('class', edgeClass);
      edgePath.setAttribute('marker-end', isHighlighted ? 'url(#arrow-selected)' : (edge.is_composite ? 'url(#arrow-composite)' : 'url(#arrow)'));

      svgLayer.appendChild(edgePath);
    });
  }

  // Selection & Details (Inspector)
  function selectEntity(id) {
    state.selectedEntityId = id;

    // Update list selection highlight
    var listButtons = entitiesListEl.querySelectorAll('.entity-item-btn');
    listButtons.forEach(function (b) { b.classList.remove('selected'); });

    // Update cards highlight
    var cards = cardsLayer.querySelectorAll('.erd-card');
    cards.forEach(function (c) {
      if (c.getAttribute('data-id') === id) {
        c.classList.add('selected');
      } else {
        c.classList.remove('selected');
      }
    });

    renderEdges();
    renderInspector(id);
  }

  function focusCard(id) {
    var pos = state.cardPositions[id];
    if (!pos) return;
    var containerW = canvasContainer.clientWidth;
    var containerH = canvasContainer.clientHeight;
    state.panX = (containerW / 2) - (pos.x + 125) * state.zoom;
    state.panY = (containerH / 2) - (pos.y + 100) * state.zoom;
    updateViewportTransform();
  }

  function renderInspector(id) {
    if (!state.erd) return;
    var node = null;
    state.erd.nodes.forEach(function (n) { if (n.id === id) node = n; });
    if (!node) return;

    inspectorTitle.textContent = node.name;

    // Badges & description
    var html =
      '<div class="inspector-meta">' +
        '<div class="inspector-badge-row">' +
          '<span class="badge kind-' + escapeHtml(node.kind) + '">' + (node.kind === 'view' ? 'Vista' : 'Tabla') + '</span>' +
          '<span class="badge">Esquema: ' + escapeHtml(node.schema) + '</span>' +
          '<span class="badge status-' + escapeHtml(node.provenance.status || 'declarada') + '">' + escapeHtml(node.provenance.status || '') + '</span>' +
        '</div>' +
        '<p class="inspector-desc">' + escapeHtml(node.description || 'Sin descripción disponible.') + '</p>' +
        (node.provenance.evidence ? '<div class="inspector-evidence"><strong>Evidencia:</strong> ' + escapeHtml(node.provenance.evidence) + '</div>' : '') +
      '</div>';

    // Columns Table
    html += '<h3 class="section-title">Columnas (' + (node.columns || []).length + ')</h3>';
    html += '<table class="meta-table"><thead><tr><th>Columna</th><th>Tipo</th><th>Clave</th><th>Nullable</th></tr></thead><tbody>';
    (node.columns || []).forEach(function (c) {
      var keyText = '-';
      if (c.key === 'primary') keyText = '<span class="key-icon pk">PK</span>';
      else if (c.key === 'foreign') keyText = '<span class="key-icon fk">FK</span>';

      html +=
        '<tr>' +
          '<td><strong>' + escapeHtml(c.name) + '</strong><br><small class="placeholder-text">' + escapeHtml(c.description || '') + '</small></td>' +
          '<td><code>' + escapeHtml(c.type) + '</code></td>' +
          '<td>' + keyText + '</td>' +
          '<td>' + (c.nullable ? 'Sí' : 'No') + '</td>' +
        '</tr>';
    });
    html += '</tbody></table>';

    // Indexes Table
    if (node.indexes && node.indexes.length) {
      html += '<h3 class="section-title">Índices (' + node.indexes.length + ')</h3>';
      html += '<table class="meta-table"><thead><tr><th>Nombre</th><th>Columnas</th><th>Único</th></tr></thead><tbody>';
      node.indexes.forEach(function (ix) {
        html +=
          '<tr>' +
            '<td><strong>' + escapeHtml(ix.name) + '</strong></td>' +
            '<td>' + escapeHtml((ix.columns || []).join(', ')) + '</td>' +
            '<td>' + (ix.unique ? 'Sí' : 'No') + '</td>' +
          '</tr>';
      });
      html += '</tbody></table>';
    }

    inspectorContent.innerHTML = html;

    // Relationships section
    renderInspectorRelationships(id);
  }

  function renderInspectorRelationships(id) {
    if (!state.erd) return;
    var relatedEdges = state.erd.edges.filter(function (e) {
      return e.from_entity === id || e.to_entity === id;
    });

    if (!relatedEdges.length) {
      inspectorDiagram.innerHTML = '<p class="placeholder-text">No hay relaciones documentadas para esta entidad en este catálogo.</p>';
      return;
    }

    var relHtml = '';
    relatedEdges.forEach(function (rel) {
      var isOut = (rel.from_entity === id);
      var otherEntity = isOut ? rel.to_entity : rel.from_entity;
      var compositeClass = rel.is_composite ? ' is-composite' : '';
      var partialClass = (rel.coverage === 'partial') ? ' is-partial' : '';

      var colsDisplay = rel.is_composite ? ('(' + rel.columns.join(', ') + ')') : rel.columns[0];
      var refColsDisplay = rel.is_composite ? ('(' + rel.ref_columns.join(', ') + ')') : rel.ref_columns[0];

      relHtml +=
        '<div class="relation-card' + compositeClass + partialClass + '">' +
          '<div class="rel-header">' +
            '<span class="rel-name">' + escapeHtml(rel.name) + '</span>' +
            '<span class="badge">' + (rel.is_composite ? 'FK Compuesta' : 'FK Simple') + '</span>' +
          '</div>' +
          '<div class="rel-flow">' +
            '<span>' + (isOut ? '→ ' : '← ') + escapeHtml(otherEntity) + '</span>' +
          '</div>' +
          '<div style="margin-top:0.3rem;">' +
            '<span>' + escapeHtml(colsDisplay) + ' ➔ ' + escapeHtml(refColsDisplay) + '</span>' +
          '</div>' +
          '<div style="font-size:0.7rem; color:#64748b; margin-top:0.2rem;">' +
            'Cardinalidad: ' + escapeHtml(rel.cardinality || 'desconocida') +
          '</div>' +
          (rel.coverage === 'partial' ? '<div class="rel-coverage-note">Cobertura parcial: referencias externas incompletas en este lote.</div>' : '') +
        '</div>';
    });

    inspectorDiagram.innerHTML = relHtml;
  }

  // Alias for backward compatibility with frontend contract tests
  function renderDiagram(id) {
    renderInspectorRelationships(id);
  }

  // Dragging cards
  function startDraggingCard(id, mouseEvent) {
    state.draggingCard = id;
    var pos = state.cardPositions[id] || { x: 50, y: 50 };
    state.cardDragStartX = mouseEvent.clientX - pos.x * state.zoom;
    state.cardDragStartY = mouseEvent.clientY - pos.y * state.zoom;

    function onMouseMove(e) {
      if (!state.draggingCard) return;
      var newX = (e.clientX - state.cardDragStartX) / state.zoom;
      var newY = (e.clientY - state.cardDragStartY) / state.zoom;
      state.cardPositions[state.draggingCard] = { x: Math.round(newX), y: Math.round(newY) };

      var cardEl = cardsLayer.querySelector('.erd-card[data-id="' + state.draggingCard + '"]');
      if (cardEl) {
        cardEl.style.left = Math.round(newX) + 'px';
        cardEl.style.top = Math.round(newY) + 'px';
      }
      renderEdges();
    }

    function onMouseUp() {
      state.draggingCard = null;
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    }

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  // Canvas Pan & Zoom Events
  function bindEvents() {
    // Pan canvas with mouse drag on background
    canvasContainer.addEventListener('mousedown', function (e) {
      if (e.target !== canvasContainer && e.target !== viewportEl && e.target !== svgLayer && e.target !== cardsLayer) {
        return;
      }
      state.isPanning = true;
      canvasContainer.classList.add('panning');
      state.startPanMouseX = e.clientX - state.panX;
      state.startPanMouseY = e.clientY - state.panY;
    });

    window.addEventListener('mousemove', function (e) {
      if (!state.isPanning) return;
      state.panX = e.clientX - state.startPanMouseX;
      state.panY = e.clientY - state.startPanMouseY;
      updateViewportTransform();
    });

    window.addEventListener('mouseup', function () {
      if (state.isPanning) {
        state.isPanning = false;
        canvasContainer.classList.remove('panning');
      }
    });

    // Zoom with mouse wheel
    canvasContainer.addEventListener('wheel', function (e) {
      e.preventDefault();
      var rect = canvasContainer.getBoundingClientRect();
      var mouseX = e.clientX - rect.left;
      var mouseY = e.clientY - rect.top;
      var zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
      setZoom(state.zoom * zoomFactor, mouseX, mouseY);
    }, { passive: false });

    // Toolbar Zoom Buttons
    btnZoomIn.addEventListener('click', function () {
      var rect = canvasContainer.getBoundingClientRect();
      setZoom(state.zoom * 1.25, rect.width / 2, rect.height / 2);
    });

    btnZoomOut.addEventListener('click', function () {
      var rect = canvasContainer.getBoundingClientRect();
      setZoom(state.zoom * 0.8, rect.width / 2, rect.height / 2);
    });

    btnZoomReset.addEventListener('click', function () {
      state.zoom = 1;
      state.panX = 40;
      state.panY = 40;
      updateViewportTransform();
    });

    btnLayout.addEventListener('click', function () {
      if (state.erd) {
        computeInitialLayout(state.erd.nodes, true);
        renderAll();
      }
    });

    // Filtering & Searching
    schemaFilterEl.addEventListener('change', function () {
      state.filterSchema = schemaFilterEl.value;
      loadErd();
    });

    kindFilterEl.addEventListener('change', function () {
      state.filterKind = kindFilterEl.value;
      renderAll();
    });

    searchInput.addEventListener('input', function () {
      state.filterQuery = searchInput.value.trim();
      loadErd();
    });

    btnCloseInspector.addEventListener('click', function () {
      state.selectedEntityId = null;
      inspectorTitle.textContent = 'Detalle';
      inspectorContent.innerHTML = '<p class="placeholder-text">Seleccioná una tabla o vista en el lienzo o en el índice para inspeccionar su ficha técnica.</p>';
      inspectorDiagram.innerHTML = '<p class="placeholder-text">Sin entidad seleccionada.</p>';
      renderAll();
    });
  }

  // Kickoff
  init();
})();

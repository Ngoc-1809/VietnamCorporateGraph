import { MultiDirectedGraph, UndirectedGraph } from 'graphology';
import circlepack from 'graphology-layout/circlepack';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import FA2Layout from 'graphology-layout-forceatlas2/worker';
import Sigma from 'sigma';

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const num = (value, digits = 0) => Number(value || 0).toLocaleString('vi-VN', { maximumFractionDigits: digits });
const params = new URLSearchParams(location.search);
const TYPES = { PERSON: '#4c77a2', ORGANIZATION: '#477f76', BANK: '#306d91',
  REGULATOR: '#896793', GOVERNMENT_AGENCY: '#916a50', BOND_ISSUE: '#88915a', BOND: '#88915a' };
const PREDICATES = { CEO_OF: 'Tổng giám đốc', CHAIR_OF: 'Chủ tịch', BOARD_MEMBER_OF: 'HĐQT',
  FOUNDED: 'Sáng lập', OWNS_SHARES_IN: 'Sở hữu cổ phần', SUBSIDIARY_OF: 'Công ty con',
  ACQUIRED: 'Mua lại', LENDS_TO: 'Cho vay', ISSUED_BOND: 'Phát hành trái phiếu',
  JOINT_VENTURE_WITH: 'Liên doanh', PARTNERS_WITH: 'Hợp tác', SANCTIONED_BY: 'Xử phạt',
  PROSECUTED_BY: 'Khởi tố / truy tố' };
const state = { mode: params.get('mode') === 'quarantine' ? 'quarantine' : 'passed',
  view: params.get('node') ? 'neighborhood' : ['overview', 'global'].includes(params.get('view')) ? params.get('view') : 'overview',
  focusId: params.get('node'), communityId: null, target: null, metrics: null, options: null,
  graphData: null, renderer: null, layout: null, request: 0,
  limits: { global: [300, 700], neighborhood: [80, 200] } };

async function api(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { detail = response.statusText; }
    throw Error(detail || response.statusText);
  }
  return response.json();
}

function seededRandom(seed) {
  let value = seed >>> 0;
  return () => { value = (1664525 * value + 1013904223) >>> 0; return value / 4294967296; };
}

function destroyGraph() {
  if (state.layout) { state.layout.stop(); state.layout = null; }
  if (state.renderer) { state.renderer.kill(); state.renderer = null; }
  $('#graph').replaceChildren();
}

function selectedValues(container, kind) {
  const boxes = [...$(container).querySelectorAll('input[type=checkbox]')];
  const checked = boxes.filter(box => box.checked).map(box => box.value);
  return checked.length === boxes.length ? [] : checked.length ? checked : [`__NO_${kind}__`];
}

function controls() {
  const maxNode = Math.max(1, Number(state.metrics?.node_count || 30000));
  const maxEdge = Math.max(0, Number(state.metrics?.edge_count || 50000));
  const nodeLimit = Math.min(maxNode, Math.max(1, Number($('#node-limit').value) || 1));
  const edgeLimit = Math.min(maxEdge, Math.max(0, Number($('#edge-limit').value) || 0));
  const minDegree = Math.min(1000, Math.max(0, Number($('#min-degree').value) || 0));
  $('#node-limit').value = nodeLimit;
  $('#edge-limit').value = edgeLimit;
  $('#min-degree').value = minDegree;
  return { nodeLimit, edgeLimit, minDegree, hops: Number($('#hops').value),
    types: selectedValues('#type-filters', 'TYPE'), predicates: selectedValues('#predicate-filters', 'RELATION') };
}

function filterQuery(filters) {
  const query = new URLSearchParams({ mode: state.mode, min_incident_edges: filters.minDegree });
  filters.types.forEach(value => query.append('types', value));
  filters.predicates.forEach(value => query.append('predicates', value));
  return query;
}

function syncUrl() {
  const query = new URLSearchParams({ mode: state.mode, view: state.view });
  if (state.focusId && state.view === 'neighborhood') query.set('node', state.focusId);
  history.replaceState(null, '', '?' + query);
}

function setActiveView() {
  document.querySelectorAll('#view-tabs button').forEach(button =>
    button.classList.toggle('active', button.dataset.view === state.view ||
      (state.view === 'community' && button.dataset.view === 'global')));
  $('#filter-note').textContent = state.view === 'overview'
    ? 'Ở Tổng quan, giới hạn node/cạnh áp dụng sau khi mở mạng chi tiết.'
    : 'Giới hạn là mức tối đa. Số thực vẽ có thể thấp hơn khi bộ lọc loại cạnh hoặc node.';
  const overview = state.view === 'overview';
  $('#node-limit').disabled = overview;
  $('#edge-limit').disabled = overview;
  $('#hops').disabled = state.view !== 'neighborhood';
}

function setView(view, focusId = null, communityId = null) {
  if (view === 'neighborhood' && !focusId) {
    $('#graph-note').textContent = 'Hãy tìm hoặc click một node để mở mạng quanh nó.';
    return;
  }
  if (state.view !== view && (view === 'global' || view === 'neighborhood' || view === 'community')) {
    const pair = state.limits[view === 'neighborhood' ? 'neighborhood' : 'global'];
    $('#node-limit').value = pair[0];
    $('#edge-limit').value = pair[1];
  }
  state.view = view;
  state.focusId = view === 'neighborhood' ? focusId : null;
  state.communityId = view === 'community' ? communityId : null;
  setActiveView();
  syncUrl();
  renderGraph();
}

function checkboxes(selector, counts, label) {
  $(selector).replaceChildren(...Object.entries(counts).map(([value, count]) => {
    const wrapper = document.createElement('label');
    wrapper.innerHTML = `<input type="checkbox" value="${esc(value)}" checked>
      <span>${esc(label(value))}</span><small>${num(count)}</small>`;
    return wrapper;
  }));
}

async function loadMode() {
  const expected = state.mode;
  try {
    const [metrics, options] = await Promise.all([
      api('/api/stats?mode=' + expected), api('/api/graph/options?mode=' + expected)]);
    if (state.mode !== expected) return;
    state.metrics = metrics;
    state.options = options;
    $('#summary').innerHTML = `<div><b>${num(metrics.node_count)}</b><span>node nguồn</span></div>
      <div><b>${num(metrics.edge_count)}</b><span>${expected === 'passed' ? 'cạnh qua QA' : 'cạnh ứng viên'}</span></div>
      <div><b>${num(metrics.relation_types)}</b><span>loại quan hệ</span></div>
      <div><b>${num(metrics.analysis.largest_component)}</b><span>node trong thành phần lớn nhất</span></div>`;
    $('#mode-note').textContent = expected === 'passed'
      ? 'Mạng Passed chỉ gồm quan hệ đã qua cổng QA tự động; đây chưa phải đánh giá gold.'
      : 'Mạng Quarantine gồm ứng viên cần rà soát. Cạnh tên chung và sự kiện bị phủ định chỉ có ở bảng quan hệ.';
    $('#quality-badge').textContent = expected.toUpperCase();
    document.body.classList.toggle('quarantine-mode', expected === 'quarantine');
    checkboxes('#type-filters', options.types, value => value);
    checkboxes('#predicate-filters', options.predicates, value => PREDICATES[value] || value);
    $('#node-limit').max = metrics.node_count;
    $('#edge-limit').max = metrics.edge_count;
    renderGraph();
  } catch (error) { $('#summary').textContent = error.message; }
}

function graphMessage(message) {
  destroyGraph();
  const element = document.createElement('div');
  element.className = 'graph-message';
  element.textContent = message;
  $('#graph').append(element);
}

function buildGraph(data) {
  const overview = data.view === 'overview';
  const graph = overview ? new UndirectedGraph() : new MultiDirectedGraph();
  for (const node of data.nodes) {
    const count = overview ? node.member_count : node.incident_edges;
    graph.addNode(node.id, { label: node.name, name: node.name, type: node.type,
      community: overview ? node.id : node.community,
      component: overview ? node.id : node.component,
      size: overview ? 5 + Math.min(18, Math.sqrt(count) * 1.05) :
        4 + Math.min(11, Math.sqrt(count) * 0.95),
      color: overview ? '#456f91' : TYPES[node.type] || '#72869a' });
  }
  for (const edge of data.edges) {
    if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target) || edge.source === edge.target) continue;
    graph.addEdgeWithKey(edge.uid, edge.source, edge.target, {
      color: state.mode === 'quarantine' ? '#c9ae89' : '#b7c7d3',
      size: overview ? Math.min(4, 1 + Math.log1p(edge.weight) / 2) : 1.1 });
  }
  circlepack.assign(graph, { hierarchyAttributes: overview ? [] : ['component', 'community'],
    rng: seededRandom(317) });
  if (data.view === 'neighborhood' && data.focus_id && graph.hasNode(data.focus_id)) {
    graph.setNodeAttribute(data.focus_id, 'x', 0);
    graph.setNodeAttribute(data.focus_id, 'y', 0);
    data.nodes.filter(node => node.id !== data.focus_id)
      .sort((a, b) => (a.hop ?? 0) - (b.hop ?? 0) || b.incident_edges - a.incident_edges || a.id.localeCompare(b.id))
      .forEach((node, index) => {
        const angle = index * 2.399963229728653;
        const radius = 18 + 3.2 * Math.sqrt(index);
        graph.setNodeAttribute(node.id, 'x', radius * Math.cos(angle));
        graph.setNodeAttribute(node.id, 'y', radius * Math.sin(angle));
      });
  }
  return graph;
}

function graphHeading(data) {
  const names = { overview: 'Cộng đồng trong mạng', global: 'Các node trong toàn mạng',
    community: `Cộng đồng ${state.communityId}`, neighborhood: 'Mạng quanh node được chọn' };
  $('#graph-title').textContent = names[data.view];
  $('#graph-eyebrow').textContent = data.view === 'overview' ? 'BẢN ĐỒ TỔNG QUAN' :
    data.view === 'neighborhood' ? 'CHÂN DUNG MẠNG' : 'SƠ ĐỒ NODE & CẠNH';
  const c = data.counts;
  $('#graph-counts').textContent = data.view === 'overview'
    ? `${num(c.filtered_nodes)} node · ${num(c.filtered_edges)} cạnh đủ lọc · ${num(c.shown_communities)}/${num(c.total_communities)} cộng đồng mở riêng`
    : `${num(c.drawn_nodes)}/${num(c.filtered_nodes)} node · ${num(c.drawn_edges)}/${num(c.filtered_edges)} cạnh được vẽ`;
  $('#graph-note').textContent = data.view === 'overview'
    ? 'Mỗi chấm là một cộng đồng; kích thước theo số node. Click để mở, hoặc chọn “Hiện tất cả sau lọc”.'
    : c.truncated_nodes || c.truncated_edges
      ? 'Đã cắt theo giới hạn. Tăng số node/cạnh ở bộ điều khiển để xem thêm.'
      : 'Kéo để di chuyển · cuộn để phóng to · click node để mở mạng quanh nó.';
}

async function renderGraph() {
  if (!state.metrics) return;
  const ticket = ++state.request;
  const filters = controls();
  const query = filterQuery(filters);
  const overview = state.view === 'overview';
  let url = '/api/graph/' + (overview ? 'overview' : 'subgraph');
  if (!overview) {
    query.set('scope', state.view);
    query.set('max_nodes', filters.nodeLimit);
    query.set('max_edges', filters.edgeLimit);
    query.set('hops', filters.hops);
    if (state.view === 'neighborhood') query.set('node_id', state.focusId);
    if (state.view === 'community') query.set('community_id', state.communityId);
  }
  url += '?' + query;
  $('#graph-counts').textContent = 'Đang lọc và bố trí mạng…';
  try {
    const data = await api(url);
    if (ticket !== state.request) return;
    state.graphData = data;
    graphHeading(data);
    if (!data.nodes.length) { graphMessage('Không có node thỏa bộ lọc. Giảm bậc tối thiểu hoặc chọn thêm loại quan hệ.'); return; }
    destroyGraph();
    const graph = buildGraph(data);
    const renderer = new Sigma(graph, $('#graph'), { settings: {
      renderLabels: data.nodes.length < 1200,
      itemSizesReference: overview ? 'positions' : 'screen',
      labelDensity: overview ? 0.25 : data.nodes.length > 40 ? 0.3 : 0.8,
      labelRenderedSizeThreshold: overview ? 10 : data.nodes.length > 40 ? 7 : 5,
      renderEdgeLabels: false,
      enableEdgeEvents: !overview && data.edges.length <= 2500,
      hideEdgesOnMove: data.edges.length > 3000,
      minCameraRatio: 0.015,
      maxCameraRatio: 5
    } });
    state.renderer = renderer;
    renderer.on('clickNode', ({ node }) => {
      if (overview) {
        if (node === 'community:other') {
          setView('global');
        } else {
          setView('community', null, Number(node.split(':')[1]));
        }
      } else {
        focusNode(node);
      }
    });
    if (!overview && data.edges.length <= 2500) renderer.on('clickEdge', ({ edge }) => showEdge(edge));
    if (state.view === 'neighborhood' && data.nodes.length <= 20 && data.edges.length) {
      state.layout = new FA2Layout(graph, { settings: { ...forceAtlas2.inferSettings(graph),
        barnesHutOptimize: true, gravity: 1.5, slowDown: 5 } });
      state.layout.start();
      const active = state.layout;
      setTimeout(() => { if (state.layout === active) active.stop(); }, 1700);
    }
    if (state.view === 'neighborhood') {
      const focused = data.nodes.find(node => node.id === state.focusId);
      if (focused) showNode(focused);
    }
  } catch (error) { if (ticket === state.request) graphMessage(error.message); }
}

function focusNode(id) {
  state.target = null;
  $('#target').value = '';
  $('#ask').disabled = true;
  setView('neighborhood', id);
}

function showNode(node) {
  const isQ = state.mode === 'quarantine';
  $('#inspector').innerHTML = `${isQ ? '<p class="candidate-warning">Ứng viên chưa kiểm định · kiểm tra bài báo trước khi kết luận.</p>' : ''}
    <div class="subtitle">${esc(node.type)} · ${esc(node.identity_status || '')}</div>
    <h3>${esc(node.name)}</h3><div class="subtitle">${esc(node.id)}</div>
    <div class="stat-grid"><div class="stat"><b>${num(node.incident_edges)}</b><span>Quan hệ kề sau lọc</span></div>
      <div class="stat"><b>${num(node.degree)}</b><span>Bậc snapshot</span></div>
      <div class="stat"><b>${num(node.pagerank, 6)}</b><span>PageRank snapshot</span></div>
      <div class="stat"><b>${num(node.core_number)}</b><span>k-core snapshot</span></div></div>
    <button type="button" class="inline-action" id="focus-current">Vẽ mạng quanh node này</button>`;
  $('#focus-current').onclick = () => focusNode(node.id);
  const rows = (state.graphData?.edges || []).filter(edge => edge.source === node.id || edge.target === node.id);
  const byId = new Map((state.graphData?.nodes || []).map(item => [item.id, item]));
  $('#relation-list').innerHTML = `<h4>${num(rows.length)} cạnh đang vẽ sát node này</h4>${rows.slice(0, 40).map(edge => {
    const other = byId.get(edge.source === node.id ? edge.target : edge.source);
    return `<button type="button" class="relation-item" data-edge="${esc(edge.uid)}">
      <strong>${esc(edge.source === node.id ? '→' : '←')} ${esc(edge.predicate)}</strong>
      <span>${esc(other?.name || 'Node khác')} · ${num(edge.article_count)} bài</span></button>`;
  }).join('')}${rows.length > 40 ? '<p class="help">Hiện 40 cạnh đầu; tăng giới hạn và click cạnh trên sơ đồ để xem chứng cứ.</p>' : ''}`;
  $('#relation-list').querySelectorAll('[data-edge]').forEach(button => button.onclick = () => showEdge(button.dataset.edge));
  if (isQ) loadReview(node.id);
  $('#ask').disabled = !state.target;
}

async function loadReview(nodeId, offset = 0) {
  const expected = state.mode;
  try {
    const result = await api(`/api/graph/review/${encodeURIComponent(nodeId)}?offset=${offset}&limit=20`);
    if (state.mode !== expected || state.view !== 'neighborhood' || state.focusId !== nodeId) return;
    let section = $('#review-relations');
    if (!section) {
      section = document.createElement('div');
      section.id = 'review-relations';
      $('#relation-list').append(section);
    }
    if (!offset) {
      section.innerHTML = `<h4>${num(result.total)} quan hệ chỉ để rà soát</h4>
        <p class="help">Tên chung, định danh yếu hoặc trạng thái không phù hợp không được vẽ thành cạnh.</p>`;
    }
    for (const edge of result.relations) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'relation-item review-item';
      button.innerHTML = `<strong>${esc(edge.subject_name)} → ${esc(edge.predicate)} → ${esc(edge.object_name)}</strong>
        <span>${esc(edge.endpoint_quality)} · ${esc(edge.factual_status)} · ${num(edge.article_count)} bài</span>`;
      button.onclick = () => showEdge(edge.edge_uid);
      section.append(button);
    }
    section.querySelector('#more-review')?.remove();
    if (offset + result.relations.length < result.total) {
      const more = document.createElement('button');
      more.id = 'more-review'; more.type = 'button'; more.className = 'inline-action';
      more.textContent = 'Xem thêm quan hệ cần rà soát';
      more.onclick = () => loadReview(nodeId, offset + result.relations.length);
      section.append(more);
    }
  } catch (error) {
    if (state.mode === expected) $('#relation-list').textContent = error.message;
  }
}

async function showEdge(uid) {
  const data = state.graphData;
  if (!data || data.view === 'overview') return;
  const expectedMode = state.mode;
  $('#inspector').innerHTML = '<p class="muted">Đang tải bằng chứng…</p>';
  try {
    const result = await api(`/api/graph/edge/${encodeURIComponent(uid)}?mode=${expectedMode}&limit=20`);
    if (expectedMode !== state.mode) return;
    const edge = result.edge;
    const qReasons = edge.quarantine_classes ? JSON.parse(edge.quarantine_classes) : [];
    $('#inspector').innerHTML = `${expectedMode === 'quarantine' ? '<p class="candidate-warning">QUARANTINE · Quan hệ ứng viên chưa được xác nhận.</p>' : ''}
      <div class="subtitle">${esc(edge.predicate)} · ${esc(edge.factual_status)}</div>
      <h3>${esc(edge.subject_name)} → ${esc(edge.object_name)}</h3>
      <p class="subtitle">${num(edge.article_count)} bài · ${num(result.total)} bằng chứng</p>
      ${qReasons.map(reason => `<span class="tag">${esc(reason)}</span>`).join('')}
      <div id="edge-evidence">${result.evidence.map(source => `<div class="evidence">
        ${expectedMode === 'quarantine' ? `<span class="tag">${esc(source.factual_status || '')}</span>` : ''}
        <p>${esc(source.evidence_text || '')}</p>
        <small><a href="${esc(source.source_url || '#')}" target="_blank" rel="noopener noreferrer">${esc(source.publisher || 'Bài báo')}</a>
        · ${esc(source.published_at || 'Không rõ ngày')}</small></div>`).join('')}</div>
      ${result.total > result.evidence.length ? `<button id="more-evidence" class="inline-action" type="button">Xem thêm bằng chứng</button>` : ''}`;
    $('#relation-list').innerHTML = '<p class="help">Click node để quay lại danh sách quan hệ của node đó.</p>';
    const more = $('#more-evidence');
    if (more) more.onclick = () => loadMoreEvidence(uid, result.evidence.length, result.total, expectedMode);
  } catch (error) { $('#inspector').textContent = error.message; }
}

async function loadMoreEvidence(uid, offset, total, expectedMode) {
  const result = await api(`/api/graph/edge/${encodeURIComponent(uid)}?mode=${expectedMode}&offset=${offset}&limit=20`);
  if (state.mode !== expectedMode) return;
  const container = $('#edge-evidence');
  for (const source of result.evidence) {
    const element = document.createElement('div');
    element.className = 'evidence';
    element.innerHTML = `<p>${esc(source.evidence_text || '')}</p><small><a href="${esc(source.source_url || '#')}"
      target="_blank" rel="noopener noreferrer">${esc(source.publisher || 'Bài báo')}</a> · ${esc(source.published_at || '')}</small>`;
    container.append(element);
  }
  const next = offset + result.evidence.length;
  if (next >= total || !result.evidence.length) $('#more-evidence')?.remove();
  else $('#more-evidence').onclick = () => loadMoreEvidence(uid, next, total, expectedMode);
}

function searchBox(input, output, onChoose) {
  let timer;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    const query = input.value.trim();
    if (query.length < 2) { output.replaceChildren(); return; }
    const expected = state.mode;
    timer = setTimeout(async () => {
      try {
        const rows = await api(`/api/search?mode=${expected}&q=${encodeURIComponent(query)}&limit=15`);
        if (expected !== state.mode || input.value.trim() !== query) return;
        output.replaceChildren(...rows.map(row => {
          const button = document.createElement('button');
          button.type = 'button';
          button.innerHTML = `${esc(row.name)}<small>${esc(row.entity_type)} · bậc ${num(row.degree)}</small>`;
          button.onclick = () => { output.replaceChildren(); input.value = row.name; onChoose(row); };
          return button;
        }));
        if (!rows.length) output.textContent = 'Không tìm thấy node.';
      } catch (error) { output.textContent = error.message; }
    }, 200);
  });
}

async function ask() {
  if (!state.focusId || !state.target) return;
  const question = $('#question').value.trim() || 'Hai thực thể liên hệ với nhau như thế nào?';
  $('#answer').textContent = 'Đang tìm đường đi và chứng cứ…';
  try {
    const result = await api('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: state.mode, start_id: state.focusId,
        target_id: state.target.node_id, question }) });
    $('#answer').innerHTML = `<p>${esc(result.answer)}</p><small>${esc(result.path.retrieval_backend)} ·
      ${result.path.hops ?? 'không có'} bước · ${result.model_used ? 'Qwen3.5:9b' : 'trình bày từ graph'}</small>
      ${result.sources.map(source => `<div class="source">[${source.number}] ${esc(source.subject)} →
        ${esc(source.predicate)} → ${esc(source.object)} · <a href="${esc(source.evidence[0]?.source_url || '#')}"
        target="_blank" rel="noopener noreferrer">${esc(source.evidence[0]?.publisher || 'Bài báo')}</a></div>`).join('')}`;
  } catch (error) { $('#answer').textContent = error.message; }
}

$('#mode').value = state.mode;
$('#mode').onchange = event => {
  state.mode = event.target.value;
  state.view = 'overview'; state.focusId = null; state.communityId = null; state.target = null;
  state.metrics = null; state.options = null; state.graphData = null; ++state.request;
  destroyGraph();
  $('#inspector').innerHTML = '<p class="muted">Click cộng đồng, node hoặc cạnh để xem chi tiết.</p>';
  $('#relation-list').replaceChildren(); $('#search').value = ''; $('#target').value = '';
  $('#search-results').replaceChildren(); $('#target-results').replaceChildren();
  $('#ask').disabled = true; $('#answer').textContent = 'Chọn node nguồn và đích để hỏi.';
  setActiveView(); syncUrl(); loadMode();
};
$('#view-tabs').querySelectorAll('button').forEach(button => button.onclick = () =>
  setView(button.dataset.view, button.dataset.view === 'neighborhood' ? state.focusId : null));
$('#apply').onclick = () => {
  const { nodeLimit, edgeLimit } = controls();
  if (state.view === 'global' || state.view === 'community') state.limits.global = [nodeLimit, edgeLimit];
  if (state.view === 'neighborhood') state.limits.neighborhood = [nodeLimit, edgeLimit];
  renderGraph();
};
$('#reset').onclick = () => {
  $('#min-degree').value = 1; $('#hops').value = 1;
  document.querySelectorAll('.checks input').forEach(box => { box.checked = true; });
  state.limits = { global: [300, 700], neighborhood: [80, 200] };
  const pair = state.view === 'neighborhood' ? state.limits.neighborhood : state.limits.global;
  $('#node-limit').value = pair[0]; $('#edge-limit').value = pair[1]; renderGraph();
};
$('#show-all').onclick = () => {
  if (!state.metrics) return;
  $('#min-degree').value = 0;
  $('#node-limit').value = state.metrics.node_count;
  $('#edge-limit').value = state.options?.eligible_edges || state.metrics.edge_count;
  state.limits.global = [Number($('#node-limit').value), Number($('#edge-limit').value)];
  setView('global');
};
$('#fit').onclick = () => state.renderer?.getCamera().animate({ x: 0.5, y: 0.5, ratio: 1 }, { duration: 350 });
$('#ask').onclick = ask;
searchBox($('#search'), $('#search-results'), row => focusNode(row.node_id));
searchBox($('#target'), $('#target-results'), row => {
  state.target = row; $('#ask').disabled = !state.focusId;
});
setActiveView();
loadMode();

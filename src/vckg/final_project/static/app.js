const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const num = (value, digits = 0) => Number(value || 0).toLocaleString('vi-VN', { maximumFractionDigits: digits });

let mode = new URLSearchParams(location.search).get('mode') === 'quarantine' ? 'quarantine' : 'passed';
let current = null;
let target = null;

async function api(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { detail = response.statusText; }
    throw Error(detail || response.statusText);
  }
  return response.json();
}

function urlWithMode(url, selectedMode = mode) {
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}mode=${selectedMode}`;
}

function hit(node, select) {
  const button = document.createElement('button');
  button.className = 'hit';
  const quality = node.endpoint_quality === 'GENERIC_NAME' ? ' · tên chung, cần định danh lại' : '';
  button.innerHTML = `<strong>${esc(node.name)}</strong><span>${esc(node.entity_type)} · ${num(node.degree)} kết nối${quality}</span>`;
  button.onclick = () => select(node);
  return button;
}

async function loadStats() {
  const selectedMode = mode;
  try {
    const metrics = await api(urlWithMode('/api/stats', selectedMode));
    if (selectedMode !== mode) return;
    const caption = mode === 'passed' ? 'dòng cạnh qua QA' : 'cạnh ứng viên';
    $('#summary').innerHTML = `<div><b>${num(metrics.node_count)}</b><span>node có cạnh</span></div>
      <div><b>${num(metrics.edge_count)}</b><span>${caption}</span></div>
      <div><b>${num(metrics.relation_types)}</b><span>loại quan hệ</span></div>
      <div><b>${num(metrics.analysis.largest_component)}</b><span>node trong thành phần lớn nhất</span></div>`;
    if (mode === 'quarantine') $('#mode-note').textContent =
      `${num(metrics.repaired_evidence_rows || 0)} dòng bằng chứng đã sửa tên chung theo bài báo; các cạnh vẫn cần kiểm định. ${num(metrics.analysis.generic_endpoint_edges_excluded_from_network)} cạnh tên chung và ${num(metrics.analysis.denied_edges_excluded_from_network || 0)} cạnh bị phủ định không được dùng cho đường đi, xếp hạng.`;
  } catch (error) { if (selectedMode === mode) $('#summary').textContent = error.message; }
}

async function loadTop() {
  const selectedMode = mode;
  try {
    const nodes = await api(urlWithMode('/api/top?limit=12', selectedMode));
    if (selectedMode === mode) $('#top').replaceChildren(...nodes.map(node => hit(node, selectNode)));
  } catch (error) { if (selectedMode === mode) $('#top').textContent = error.message; }
}

function searchBox(input, output, select) {
  let timer;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    const query = input.value.trim();
    if (query.length < 2) { output.replaceChildren(); return; }
    const selectedMode = mode;
    timer = setTimeout(async () => {
      try {
        const nodes = await api(urlWithMode('/api/search?q=' + encodeURIComponent(query), selectedMode));
        if (selectedMode !== mode || input.value.trim() !== query) return;
        output.replaceChildren(...nodes.map(node => hit(node, select)));
        if (!nodes.length) output.textContent = 'Không có kết quả trong chế độ này.';
      } catch (error) { if (selectedMode === mode) output.textContent = error.message; }
    }, 180);
  });
}

function nodeLabel(name) { return name.length > 24 ? name.slice(0, 22) + '…' : name; }

function drawGraph(data) {
  const rows = mode === 'quarantine'
    ? data.relations.filter(row => row.endpoint_quality === 'ELIGIBLE') : data.relations;
  const graph = $('#graph');
  if (!rows.length) {
    graph.textContent = mode === 'quarantine'
      ? 'Không có cạnh đủ tên để vẽ; xem các ứng viên cần rà soát bên dưới.'
      : 'Node chưa có cạnh trong chế độ này.';
    return;
  }
  const center = data.node.node_id;
  const found = new Map();
  for (const row of rows) {
    const other = row.subject_id === center
      ? { id: row.object_id, name: row.object_name }
      : { id: row.subject_id, name: row.subject_name };
    if (other.id !== center && !found.has(other.id)) found.set(other.id, other);
    if (found.size === 12) break;
  }
  const nodes = [...found.values()];
  const width = 900, height = 430, cx = 450, cy = 215;
  const left = Math.ceil(nodes.length / 2), right = nodes.length - left;
  const position = new Map(nodes.map((node, index) => {
    const side = index < left ? 0 : 1;
    const offset = side ? index - left : index;
    const count = side ? right : left;
    return [node.id, { x: side ? 650 : 250, y: count === 1 ? cy : 42 + offset * 346 / (count - 1), side }];
  }));
  let svg = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Mạng lân cận">`;
  for (const node of nodes) {
    const point = position.get(node.id);
    svg += `<line class="edge-line" x1="${cx}" y1="${cy}" x2="${point.x}" y2="${point.y}"/>`;
  }
  for (const node of nodes) {
    const point = position.get(node.id);
    svg += `<g data-node="${esc(node.id)}"><circle class="node-dot" cx="${point.x}" cy="${point.y}" r="7"/>
      <text class="node-text" x="${point.side ? point.x + 12 : point.x - 12}" y="${point.y + 4}"
      text-anchor="${point.side ? 'start' : 'end'}">${esc(nodeLabel(node.name))}</text></g>`;
  }
  svg += `<circle class="center-dot" cx="${cx}" cy="${cy}" r="15"/>
    <text class="node-text" x="${cx}" y="${cy + 34}" text-anchor="middle" font-weight="bold">${esc(nodeLabel(data.node.name))}</text></svg>`;
  graph.innerHTML = svg;
  graph.querySelectorAll('g[data-node]').forEach(element =>
    element.onclick = () => selectNode({ node_id: element.dataset.node }));
}

function quarantineReasons(row) {
  if (!row.quarantine_classes) return [];
  try { return JSON.parse(row.quarantine_classes); } catch { return [row.quarantine_classes]; }
}

function jsonList(value) {
  if (!value) return [];
  try { return JSON.parse(value); } catch { return [value]; }
}

function showRelations(data) {
  const box = $('#relations');
  box.replaceChildren();
  for (const row of data.relations) {
    const item = document.createElement('div');
    item.className = 'relation';
    const reasons = mode === 'quarantine'
      ? quarantineReasons(row).map(reason => `<span class="tag warning">${esc(reason)}</span>`).join('') : '';
    const endpointFlag = mode === 'quarantine' && row.endpoint_quality !== 'ELIGIBLE'
      ? `<span class="tag warning">${esc(row.endpoint_quality)} · không dùng trong đường đi</span>` : '';
    const repairFlag = mode === 'quarantine' && row.repair_method
      ? `<span class="tag warning">Đã sửa tên từ bài báo · vẫn cần kiểm định</span>` : '';
    const evidence = row.evidence.map(source => `<div class="evidence">${mode === 'quarantine'
      ? `<div class="evidence-meta"><span class="tag warning">${esc(source.factual_status)}</span>${quarantineReasons(source).map(reason => `<span class="tag warning">${esc(reason)}</span>`).join('')}${source.status_adjustment ? `<span class="tag warning" title="Trạng thái gốc: ${esc(jsonList(source.source_factual_statuses).join(', '))}">Đã sửa trạng thái chức vụ · cần đối chiếu</span>` : ''}</div>` : ''}${esc(source.evidence_text || 'Không có trích đoạn.')}
      <br><a href="${esc(source.source_url || '#')}" target="_blank" rel="noopener noreferrer">
      ${esc(source.publisher || 'Bài báo')} · ${esc(source.published_at || 'Không rõ ngày')}</a></div>`).join('');
    item.innerHTML = `<div class="relation-head"><button data-id="${esc(row.subject_id)}">${esc(row.subject_name)}</button>
      <span class="tag">${esc(row.predicate)}</span><button data-id="${esc(row.object_id)}">${esc(row.object_name)}</button>
      <span class="tag ${mode === 'quarantine' ? 'warning' : ''}" title="${esc(jsonList(row.factual_statuses).join(', '))}">${esc(row.factual_status)}</span>${reasons}${endpointFlag}${repairFlag}${mode === 'quarantine' ? `<span class="tag">${esc(row.article_count)} bài · ${esc(row.evidence_count)} bằng chứng</span>` : ''}</div>${evidence}`;
    item.querySelectorAll('button').forEach(button =>
      button.onclick = () => selectNode({ node_id: button.dataset.id }));
    box.append(item);
  }
  if (!data.relations.length) box.textContent = 'Không có cạnh hiển thị.';
}

async function selectNode(node) {
  const selectedMode = mode;
  try {
    const data = await api(urlWithMode('/api/profile/' + encodeURIComponent(node.node_id), selectedMode));
    if (selectedMode !== mode) return;
    current = data.node;
    history.replaceState(null, '', '?mode=' + mode + '&node=' + encodeURIComponent(current.node_id));
    $('#search').value = current.name;
    $('#search-results').replaceChildren();
    const warning = mode === 'quarantine'
      ? `<p class="candidate-warning">Ứng viên chưa kiểm định · chỉ số mạng chỉ tính từ cạnh có đầu mút đủ tên.${
          current.endpoint_quality === 'GENERIC_NAME' ? ' Tên node này quá chung, cần xác định lại từ bài báo.' : ''}${
          current.aggregation_method ? ` Gộp tạm ${jsonList(current.source_node_ids).length} ID theo tên, tổ chức và chức vụ; chưa xác minh danh tính.` : ''}</p>` : '';
    const hasNetworkPosition = mode === 'passed' || current.degree > 0;
    $('#profile').innerHTML = `${warning}<div class="type">${esc(current.entity_type)} · ${esc(current.identity_status)}</div>
      <h2>${esc(current.name)}</h2><div class="muted">${esc(current.aliases || '')}</div>
      <div class="metrics"><div class="metric"><b>${num(current.degree)}</b><span>${mode === 'quarantine' ? 'Bậc sau lọc tên chung' : 'Bậc kết nối'}</span></div>
      <div class="metric"><b>${hasNetworkPosition ? num(current.pagerank, 6) : '—'}</b><span>PageRank</span></div>
      <div class="metric"><b>${hasNetworkPosition ? num(current.community) : '—'}</b><span>Cộng đồng</span></div>
      <div class="metric"><b>${hasNetworkPosition ? num(current.core_number) : '—'}</b><span>k-core</span></div></div>`;
    drawGraph(data);
    showRelations(data);
    $('#ask').disabled = !target;
  } catch (error) { if (selectedMode === mode) $('#profile').textContent = error.message; }
}

function selectTarget(node) {
  target = node;
  $('#target').value = node.name;
  $('#target-results').replaceChildren();
  $('#ask').disabled = !current;
}

async function ask() {
  if (!current || !target) return;
  const question = $('#question').value.trim() || `${current.name} liên hệ với ${target.name} như thế nào?`;
  $('#answer').textContent = 'Đang truy xuất đường đi và chứng cứ…';
  try {
    const result = await api('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ start_id: current.node_id, target_id: target.node_id, question, mode }) });
    const box = $('#answer');
    box.replaceChildren();
    const paragraph = document.createElement('p');
    paragraph.textContent = result.answer;
    box.append(paragraph);
    const meta = document.createElement('small');
    meta.textContent = `Chế độ: ${mode.toUpperCase()} · Truy xuất: ${result.path.retrieval_backend} · `
      + `${result.path.hops ?? 'không có'} bước · ${result.model_used ? 'Qwen3.5:9b' : 'trình bày quy tắc'}`;
    box.append(meta);
    for (const source of result.sources) {
      const item = document.createElement('div');
      item.className = 'source';
      const evidence = source.evidence[0];
      item.innerHTML = `[${source.number}] ${esc(source.subject)} → ${esc(source.predicate)} → ${esc(source.object)} · `
        + `<a href="${esc(evidence.source_url || '#')}" target="_blank" rel="noopener noreferrer">`
        + `${esc(evidence.publisher || 'Bài báo')}</a><br>${esc((evidence.evidence_text || '').slice(0, 400))}`;
      box.append(item);
    }
  } catch (error) { $('#answer').textContent = error.message; }
}

function switchMode(next) {
  mode = next;
  document.body.classList.toggle('quarantine-mode', mode === 'quarantine');
  $('#mode').value = mode;
  $('#mode-note').textContent = mode === 'passed'
    ? 'Chỉ hiển thị quan hệ đã qua cổng QA của ứng dụng.'
    : 'Hiển thị toàn bộ ứng viên QUARANTINE; có thể sai danh tính, quan hệ hoặc trạng thái sự kiện.';
  $('#aside-note').textContent = mode === 'passed'
    ? 'Các chỉ số dùng lớp cạnh đã qua QA. Chúng không phải thước đo độ chính xác của mô hình.'
    : 'Các chỉ số tính riêng trên ứng viên QUARANTINE; không dùng để tuyên bố quan hệ thật hoặc chất lượng mô hình.';
  current = null;
  target = null;
  $('#search').value = '';
  $('#target').value = '';
  $('#search-results').replaceChildren();
  $('#target-results').replaceChildren();
  $('#profile').innerHTML = '<div class="empty">Chọn một node ở cột bên trái để bắt đầu.</div>';
  $('#graph').textContent = 'Chưa chọn node.';
  $('#relations').textContent = 'Chưa chọn node.';
  $('#answer').textContent = 'Chọn node nguồn và node đích để hỏi.';
  $('#ask').disabled = true;
  history.replaceState(null, '', '?mode=' + mode);
  loadStats();
  loadTop();
}

searchBox($('#search'), $('#search-results'), selectNode);
searchBox($('#target'), $('#target-results'), selectTarget);
$('#ask').onclick = ask;
$('#mode').onchange = event => switchMode(event.target.value);
const initialNode = new URLSearchParams(location.search).get('node');
switchMode(mode);
if (initialNode) selectNode({ node_id: initialNode });

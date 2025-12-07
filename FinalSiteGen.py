import pandas as pd
import html
import json
import os
from datetime import datetime
import pytz  # <--- Added pytz for NZ Time

# ---- Configuration ----
IN_CSV = "jbhifi_products_with_category.csv"
HOTLINKS_CSV = "hotlinks.csv"
OUT_HTML = "index.html" # <--- Changed to index.html for GitHub Pages
WHATS_NEW_FILE = "whatsnew.txt"

# Base URL for constructing links from handles
BASE_URL = "https://www.jbhifi.co.nz/products/"

# ---- Utility Functions ----
def esc(x):
    if pd.isna(x):
        return ""
    return (
        html.escape(str(x))
        .replace("\n", " ")
        .replace("\r", " ")
        .replace(",", "&#44;")
    )

def to_numeric_price(val):
    try:
        if pd.isna(val) or val == "":
            return None
        s = str(val).strip().replace("$", "").replace(",", "")
        return float(s)
    except Exception:
        return None

def fmt_price(val):
    try:
        if pd.isna(val) or val == "":
            return ""
        v = float(str(val).replace("$", "").replace(",", ""))
        return f"${v:,.2f}"
    except Exception:
        s = str(val).strip()
        return esc(s)

def format_title_from_handle(handle):
    if pd.isna(handle) or handle == "":
        return "Unknown Product"
    text = str(handle).replace("-", " ")
    formatted = text.title()
    formatted = formatted.replace(" 4k ", " 4K ").replace(" Hd", " HD").replace(" Ps5", " PS5").replace(" Ps4", " PS4")
    return formatted

def generate_hotlinks_html():
    if not os.path.exists(HOTLINKS_CSV):
        return ""
    try:
        df_hot = pd.read_csv(HOTLINKS_CSV, header=None)
        first_cell = str(df_hot.iloc[0,0]).lower()
        if "heading" in first_cell or "label" in first_cell:
            df_hot = pd.read_csv(HOTLINKS_CSV)
            df_hot.columns = range(df_hot.shape[1])
        
        html_out = '<div class="hotlinks-section">'
        html_out += '<span class="hotlinks-label">Quick Search:</span>'
        html_out += '<div class="hotlinks-grid">'
        for _, row in df_hot.iterrows():
            if pd.isna(row[0]) or pd.isna(row[1]): continue
            label = str(row[0]).strip()
            term = str(row[1]).strip()
            html_out += f'<button class="btn hotlink-btn" onclick="runHotlink(\'{esc(term)}\')">{esc(label)}</button>'
        html_out += '</div></div>'
        return html_out
    except Exception:
        return ""

def generate_category_filters_html(cat_list):
    if not cat_list: return ""
    html_out = '<div class="controls-promo-filters">'
    html_out += '<span class="small" style="color: var(--muted); font-size: 14px; margin-right: 5px;">Filter By Category:</span>'
    html_out += '<button class="btn toggle active" data-cat="all">All</button>'
    for cat in cat_list:
        html_out += f'<button class="btn toggle cat-filter-btn" data-cat="{esc(cat).lower()}">{esc(cat)}</button>'
    html_out += "</div>"
    return html_out

# ---- Main Processing ----
try:
    df = pd.read_csv(IN_CSV)
except FileNotFoundError:
    print(f"Error: Input file '{IN_CSV}' not found.")
    df = pd.DataFrame(columns=["Product ID", "Variant ID", "Handle", "Title", "Original Price", "Discounted Price", "Discount %", "Category"])

deals_payload = []
unique_categories = set()

print(f"Processing {len(df)} rows...")

for idx, row in df.iterrows():
    pid = str(row.get("Product ID", "") or "")
    raw_handle = str(row.get("Handle", "") or "")
    
    if not raw_handle or raw_handle == "nan":
        raw_handle = str(row.get("Title", "") or "")
        formatting_source = raw_handle
        link_url = "#" 
    else:
        formatting_source = raw_handle
        link_url = BASE_URL + raw_handle

    display_title = format_title_from_handle(formatting_source)
    orig_val = to_numeric_price(row.get("Original Price"))
    disc_val = to_numeric_price(row.get("Discounted Price"))
    pct_raw = row.get("Discount %")
    
    pct_val = 0
    if pct_raw:
        pct_val = to_numeric_price(pct_raw) or 0
    elif orig_val and disc_val and orig_val > 0:
        pct_val = ((orig_val - disc_val) / orig_val) * 100

    category_raw = str(row.get("Category", "Other")).strip()
    if not category_raw or category_raw.lower() == "nan": category_raw = "Other"
    unique_categories.add(category_raw)

    deals_payload.append({
        "n": display_title, "p": pid, "l": link_url,
        "o": fmt_price(orig_val), "d": fmt_price(disc_val),
        "v": pct_val if pct_val else 0,
        "vp": disc_val if disc_val is not None else (orig_val if orig_val is not None else 0),
        "c": category_raw
    })

json_data = json.dumps(deals_payload)
sorted_categories = sorted(list(unique_categories))
category_filters_html = generate_category_filters_html(sorted_categories)
hotlinks_html = generate_hotlinks_html()

# ---- TIMEZONE FIX (Implemented from template) ----
try:
    nz_tz = pytz.timezone('Pacific/Auckland')
    scrape_time_str = datetime.now(nz_tz).strftime("%d/%m/%Y @ %I:%M %p")
except Exception as e:
    print(f"Timezone Error: {e}. Falling back to UTC.")
    scrape_time_str = datetime.now().strftime("%d/%m/%Y @ %I:%M %p UTC")

# What's New
whats_new_content = "No updates found."
if os.path.exists(WHATS_NEW_FILE):
    try:
        with open(WHATS_NEW_FILE, "r", encoding="utf-8") as f:
            whats_new_content = f.read().replace("\n", "<br>")
    except Exception: pass

# ---- HTML Output ----
html_content = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>JB Hi-Fi Deals Filterer</title>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0"/>
<script>
  (function() {{
    const theme = localStorage.getItem('theme');
    if (theme === 'dark') {{ document.documentElement.classList.add('dark'); }}
  }})();
</script>
<style>
  :root {{ 
    --accent: #E65100; --accent-dark: #BF360C; --bg: #f5f5f5; --card: #ffffff; 
    --text: #222; --muted: #666; --border: #ddd; --header-bg: #ffffff; 
    --row-even: #f9fafb; --row-hover: #eef1f5; --btn-text: #fff;
  }}
  :root.dark {{ 
    --accent: #F57C00; --accent-dark: #E65100; --bg: #121212; --card: #1E1E1E; 
    --text: #E0E0E0; --muted: #9E9E9E; --border: #333; --header-bg: #1E1E1E; 
    --row-even: #252525; --row-hover: #303030; --btn-text: #fff;
  }}
  html, body {{ width: 100%; margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 16px; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  header {{ background: var(--header-bg); border-radius: 8px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid var(--border); display: flex; flex-direction: column; gap: 15px; margin-bottom: 24px; }}
  .header-top {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
  .header-titles h1 {{ margin: 0; font-size: 24px; font-weight: 700; color: var(--text); }}
  .scrape-time {{ font-size: 13px; color: var(--muted); font-family: monospace; margin-top: 4px; }}
  .header-actions {{ display: flex; gap: 8px; align-items: center; }}
  .btn {{ background: var(--accent); color: var(--btn-text); border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }}
  .btn:hover {{ background: var(--accent-dark); }}
  .btn.secondary {{ background: transparent; color: var(--text); border: 1px solid var(--border); }}
  .btn.secondary:hover {{ background: var(--row-hover); }}
  .btn.coffee {{ background: #FF813F; color: #fff; }} .btn.coffee:hover {{ background: #E57339; }}
  .controls-main {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 10px; }}
  input, select {{ padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px; outline: none; }}
  input:focus {{ border-color: var(--accent); }}
  input[type="search"] {{ min-width: 250px; flex-grow: 1; }}
  .pct-inputs {{ display: flex; align-items: center; gap: 5px; }}
  .pct-inputs input {{ width: 60px; text-align: center; }}
  .hotlinks-section {{ display: flex; flex-direction: column; gap: 8px; margin-top: 15px; padding-top: 15px; border-top: 1px dashed var(--border); }}
  .hotlinks-grid {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .hotlink-btn {{ background: var(--bg); color: var(--text); border: 1px solid var(--border); font-size: 13px; padding: 6px 12px; border-radius: 20px; flex-grow: 0; }}
  .hotlink-btn:hover {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .controls-promo-filters {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 15px; border-top: 1px solid var(--border); padding-top:15px; }}
  .btn.toggle {{ background: var(--bg); color: var(--muted); border: 1px solid var(--border); font-size: 13px; padding: 5px 12px; border-radius: 20px; }}
  .btn.toggle:hover {{ background: var(--row-hover); color: var(--text); }}
  .btn.toggle.active {{ background: var(--accent); color: white; border-color: var(--accent); }}
  .table-container {{ overflow-x: auto; border-radius: 8px; border: 1px solid var(--border); background: var(--card); margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; min-width: 700px; }}
  thead th {{ text-align: left; padding: 14px 16px; background: var(--header-bg); border-bottom: 1px solid var(--border); cursor: pointer; font-weight: 600; font-size: 13px; text-transform: uppercase; color: var(--muted); }}
  thead th:hover {{ color: var(--text); }}
  tbody td {{ padding: 14px 16px; border-top: 1px solid var(--border); font-size: 14px; vertical-align: middle; }}
  tbody tr:nth-child(even) {{ background: var(--row-even); }}
  tbody tr:hover {{ background: var(--row-hover); }}
  .price {{ font-family: monospace; font-size: 14px; color: var(--text); white-space: nowrap; }}
  .discount {{ color: #D32F2F; font-weight: 700; white-space: nowrap; }}
  :root.dark .discount {{ color: #FF5252; }}
  .google-icon {{ width: 20px; height: 20px; fill: var(--muted); vertical-align: middle; }}
  tr:hover .google-icon {{ fill: var(--accent); }}
  a.product-link {{ color: var(--text); text-decoration: none; font-weight: 600; display: block; }}
  a.product-link:hover {{ color: var(--accent); text-decoration: underline; }}
  .pagination-bar {{ display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--header-bg); border: 1px solid var(--border); border-radius: 8px; color: var(--muted); font-size: 14px; }}
  .modal-overlay {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: none; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(2px); }}
  .modal-content {{ background: var(--card); padding: 25px; border-radius: 12px; width: 90%; max-width: 600px; max-height: 80vh; display: flex; flex-direction: column; border: 1px solid var(--border); }}
  .modal-header {{ display: flex; justify-content: space-between; border-bottom: 1px solid var(--border); padding-bottom: 15px; margin-bottom: 15px; }}
  .modal-close-btn {{ background: none; border: none; font-size: 24px; cursor: pointer; color: var(--muted); }}
  @media (max-width: 768px) {{
    .header-top {{ flex-direction: column; align-items: flex-start; }}
    .header-actions {{ width: 100%; justify-content: space-between; margin-top: 10px; }}
    .controls-main {{ flex-direction: column; align-items: stretch; }}
    input[type="search"] {{ width: 100%; }}
    .pct-inputs {{ justify-content: space-between; }} .pct-inputs input {{ width: 45%; }}
    thead th:nth-child(1), tbody td:nth-child(1), thead th:nth-child(3), tbody td:nth-child(3) {{ display: none; }}
    .pagination-bar {{ flex-direction: column; gap: 10px; text-align: center; }}
    .hotlink-btn {{ flex-grow: 1; text-align: center; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="header-top">
      <div class="header-titles">
        <h1>JB Hi-Fi Deals Filterer</h1>
        <div class="scrape-time">Last updated: {scrape_time_str}</div>
      </div>
      <div class="header-actions">
        <button class="btn secondary" id="whatsNewBtn">What's New</button>
        <a href="https://www.buymeacoffee.com/polobaggyo" target="_blank" class="btn coffee">☕ Coffee</a>
        <button class="btn icon-btn secondary" id="toggleThemeBtn">☀️</button>
      </div>
    </div>
    <div class="controls-main">
      <input id="searchInput" type="search" placeholder="Search products..." />
      <div class="pct-inputs">
        <span style="font-size:13px; color:var(--muted)">Discount %</span>
        <input id="minPct" type="number" min="0" max="100" placeholder="0" value="0" />
        <input id="maxPct" type="number" min="0" max="100" placeholder="100" value="100" />
      </div>
      <label style="display:flex;align-items:center;gap:6px;font-size:14px;color:var(--muted);">
         <input type="checkbox" id="hideZero" checked> Hide 0% Off
      </label>
      <button class="btn secondary" id="resetBtn">Reset</button>
    </div>
    <div style="display:flex; justify-content:flex-end; margin-top:5px; gap:15px; font-size:13px; color:var(--muted);">
         <span>Found: <strong id="visibleCount" style="color:var(--text)">0</strong></span>
    </div>
    {hotlinks_html}
    {category_filters_html}
  </header>
  <div class="table-container">
    <table id="dealsTable">
      <thead>
        <tr>
          <th data-sort="p">Product ID</th>
          <th data-sort="n">Title</th>
          <th data-sort="vp">Original</th>
          <th data-sort="vp">Discounted</th>
          <th data-sort="v">% Off</th>
          <th data-sort="c">Category</th>
          <th>G</th>
        </tr>
      </thead>
      <tbody id="tableBody"></tbody>
    </table>
  </div>
  <div class="pagination-bar">
    <div>Rows: <select id="rowsPerPage"><option value="50">50</option><option value="100" selected>100</option><option value="200">200</option><option value="1000">All</option></select></div>
    <div id="pageInfo">Page 1</div>
    <div style="display:flex; gap:5px;"><button class="btn secondary" id="btnPrev">Prev</button><button class="btn secondary" id="btnNext">Next</button></div>
  </div>
</div>
<div id="whatsNewModal" class="modal-overlay">
  <div class="modal-content">
    <div class="modal-header"><h2>What's New</h2><button id="closeWhatsNewBtn" class="modal-close-btn">&times;</button></div>
    <div class="modal-body">{whats_new_content}</div>
  </div>
</div>
<script>
const allData = {json_data};
const googleIconSvg = '<svg class="google-icon" viewBox="0 0 24 24"><path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .533 5.333.533 12S5.867 24 12.48 24c3.44 0 6.04-1.133 8.147-3.333 2.147-2.147 2.813-5.013 2.813-7.387 0-.747-.053-1.44-.16-2.107H12.48z"/></svg>';
let state = {{ filtered: [], currentPage: 1, rowsPerPage: 100, sortCol: 'v', sortDir: 'desc', search: '', minPct: 0, maxPct: 100, activeCategory: 'all', hideZero: true }};
const tbody = document.getElementById('tableBody');
const countEl = document.getElementById('visibleCount');
function init() {{ state.filtered = [...allData]; applyFilters(); setupListeners(); renderPage(); }}
function escapeHtml(text) {{ if (!text) return ''; return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;"); }}
function renderPage() {{
    const start = (state.currentPage - 1) * state.rowsPerPage; const end = start + state.rowsPerPage; const slice = state.filtered.slice(start, end); let html = '';
    slice.forEach(d => {{
        const googleLink = `https://www.google.com/search?q=${{encodeURIComponent(d.n)}}`;
        let linkHtml = `<span class="product-link">${{escapeHtml(d.n)}}</span>`;
        if (d.l && d.l !== '#') {{ linkHtml = `<a class="product-link" href="${{d.l}}" target="_blank">${{escapeHtml(d.n)}}</a>`; }}
        let pctDisplay = d.v > 0 ? `${{Math.round(d.v)}}%` : '';
        html += `<tr><td style="font-family:monospace; color:var(--muted);">${{escapeHtml(d.p)}}</td><td>${{linkHtml}}</td><td class="price" style="text-decoration:line-through; color:var(--muted);">${{d.o}}</td><td class="price" style="font-weight:bold;">${{d.d}}</td><td class="discount">${{pctDisplay}}</td><td><span style="background:var(--row-hover); padding:2px 8px; border-radius:4px; font-size:12px;">${{escapeHtml(d.c)}}</span></td><td style="text-align:center;"><a href="${{googleLink}}" target="_blank">${{googleIconSvg}}</a></td></tr>`;
    }});
    if (slice.length === 0) {{ html = '<tr><td colspan="7" style="text-align:center; padding:20px;">No deals found matching filters.</td></tr>'; }}
    tbody.innerHTML = html;
    const total = state.filtered.length; const maxPage = Math.ceil(total / state.rowsPerPage) || 1;
    document.getElementById('pageInfo').innerText = `Page ${{state.currentPage}} of ${{maxPage}}`;
    document.getElementById('btnPrev').disabled = state.currentPage === 1; document.getElementById('btnNext').disabled = state.currentPage >= maxPage; countEl.innerText = total;
}}
function applyFilters() {{
    const term = state.search.toLowerCase();
    state.filtered = allData.filter(d => {{
        if (state.activeCategory !== 'all' && (!d.c || d.c.toLowerCase() !== state.activeCategory)) return false;
        if (state.hideZero && d.v <= 0) return false;
        if (d.v < state.minPct || d.v > state.maxPct) return false;
        if (term && !(d.n + ' ' + d.p + ' ' + d.c).toLowerCase().includes(term)) return false;
        return true;
    }});
    state.currentPage = 1; sortData();
}}
function sortData() {{
    const col = state.sortCol; const dir = state.sortDir === 'asc' ? 1 : -1;
    state.filtered.sort((a, b) => {{
        let valA = a[col]; let valB = b[col];
        if (typeof valA === 'string') valA = valA.toLowerCase(); if (typeof valB === 'string') valB = valB.toLowerCase();
        if (col === 'vp') {{ valA = a.vp; valB = b.vp; }}
        if (valA < valB) return -1 * dir; if (valA > valB) return 1 * dir; return 0;
    }});
    renderPage();
}}
window.runHotlink = function(term) {{ document.getElementById('searchInput').value = term; state.search = term; applyFilters(); renderPage(); }}
function setupListeners() {{
    const debounce = (fn, delay) => {{ let t; return (...args) => {{ clearTimeout(t); t = setTimeout(()=>fn(...args), delay); }}; }};
    const runFilter = debounce(() => {{ applyFilters(); renderPage(); }}, 200);
    document.getElementById('searchInput').addEventListener('input', e => {{ state.search = e.target.value; runFilter(); }});
    document.getElementById('minPct').addEventListener('input', e => {{ state.minPct = parseFloat(e.target.value) || 0; runFilter(); }});
    document.getElementById('maxPct').addEventListener('input', e => {{ state.maxPct = parseFloat(e.target.value) || 100; runFilter(); }});
    document.getElementById('hideZero').addEventListener('change', e => {{ state.hideZero = e.target.checked; applyFilters(); renderPage(); }});
    document.querySelectorAll('.cat-filter-btn, [data-cat="all"]').forEach(btn => {{
        btn.addEventListener('click', (e) => {{ document.querySelectorAll('.cat-filter-btn, [data-cat="all"]').forEach(b => b.classList.remove('active')); e.currentTarget.classList.add('active'); state.activeCategory = e.currentTarget.getAttribute('data-cat'); applyFilters(); renderPage(); }});
    }});
    document.getElementById('resetBtn').addEventListener('click', () => {{ state.search = ''; state.minPct = 0; state.maxPct = 100; state.activeCategory = 'all'; state.hideZero = true; document.getElementById('searchInput').value = ''; document.getElementById('minPct').value = 0; document.getElementById('maxPct').value = 100; document.getElementById('hideZero').checked = true; document.querySelectorAll('.cat-filter-btn').forEach(b => b.classList.remove('active')); document.querySelector('[data-cat="all"]').classList.add('active'); applyFilters(); renderPage(); }});
    document.querySelectorAll('th[data-sort]').forEach(th => {{ th.addEventListener('click', () => {{ const col = th.dataset.sort; if (state.sortCol === col) {{ state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc'; }} else {{ state.sortCol = col; state.sortDir = 'desc'; }} sortData(); }}); }});
    document.getElementById('rowsPerPage').addEventListener('change', e => {{ state.rowsPerPage = parseInt(e.target.value); state.currentPage = 1; renderPage(); }});
    document.getElementById('btnPrev').addEventListener('click', () => {{ if(state.currentPage > 1) {{ state.currentPage--; renderPage(); }} }});
    document.getElementById('btnNext').addEventListener('click', () => {{ const max = Math.ceil(state.filtered.length / state.rowsPerPage); if(state.currentPage < max) {{ state.currentPage++; renderPage(); }} }});
    const toggleTheme = document.getElementById('toggleThemeBtn');
    function updateThemeIcon(isDark) {{ toggleTheme.textContent = isDark ? '🌙' : '☀️'; }}
    toggleTheme.addEventListener('click', () => {{ const isDark = document.documentElement.classList.toggle('dark'); localStorage.setItem('theme', isDark ? 'dark' : 'light'); updateThemeIcon(isDark); }});
    updateThemeIcon(document.documentElement.classList.contains('dark'));
    const modal = document.getElementById('whatsNewModal');
    document.getElementById('whatsNewBtn').addEventListener('click', () => modal.style.display = 'flex');
    document.getElementById('closeWhatsNewBtn').addEventListener('click', () => modal.style.display = 'none');
    modal.addEventListener('click', (e) => {{ if (e.target === modal) modal.style.display = 'none'; }});
}}
init();
</script>
</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ Generated {OUT_HTML} successfully.")
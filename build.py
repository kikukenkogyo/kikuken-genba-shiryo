# 各現場の資料ページを作る（img/ の画像から index.html と資料ごとのページを生成）
# 資料を足すときは SITES に足して、img/ に「キー-ページ番号.jpg」を置いてから python build.py
import pathlib, html, json

ROOT = pathlib.Path(__file__).parent
SITES = [
    ("江東区福住4階建建物解体工事", [
        ("fukuzumi-koutei", "工程表"),
        ("fukuzumi-kasetsu", "仮設計画図（修正版）"),
        ("fukuzumi-sekou", "施工計画図"),
    ]),
    ("九段南計画解体工事", [
        ("kudan-koutei", "工程表（地下解体）"),
        ("kudan-flow", "作業フロー図（地下解体）"),
        ("kudan-step", "解体の流れ・ステップ図（地下解体）"),
    ]),
    ("都営保木間第５アパート除却工事", [
        ("hokima-annai", "現場案内図"),
        ("hokima-sekou", "施工計画図"),
    ]),
    ("（仮称）世田谷区砧6-25 自走式立体駐車場解体工事", [
        ("kinuta-koutei", "工程表（10/28着工）"),
    ]),
]

# 一覧ページ（index.html）に出すのは、菊建ページ（Notion「各現場の資料」）に載せている資料だけ。
# 見積段階・提案用の3D/動画（extra.json・videos.json で足されるもの）は、ページは作るが一覧には出さない
# （2026-10-25 酒井さん：決まっていない仕事が職人さんに見えると混乱する）。一覧に出すときはここに足す
INDEX_SITES = [s for s, _ in SITES]
INDEX_LINKS = {"kudan-3d.html", "kinuta-rittyu-3d.html", "kinuta-rittyu-video.html",
               "tvtokyo-abe.html"}  # 2026-10-31 酒井さん：テレ東の動画は職人さん用の一覧にも出す
# 現場ごとの「LINEで送る用」のページ（その現場の資料だけを並べる。元請様・協力会社さんにも送れる）。{"ファイル名": "現場名"}
SHARE_PAGES = {"kinuta-rittyu.html": "（仮称）世田谷区砧6-25 自走式立体駐車場解体工事"}  # 2026-10-27 酒井さん
# 酒井さん専用の一覧（見積段階の3D・動画も含めて全部。iPad のホーム画面用）。名前は推測されにくくしてある
ALL_INDEX = "sakai-c9521c84.html"
# 酒井さん専用の一覧は「受注した工事」と「見積段階」に分けて出す（2026-10-29 酒井さん）。受注したら、ここに現場名を足す
# （菊建ページ＝Notion に載せている現場は受注した工事。それ以外は見積段階として下に出る）
UKEOI_SITES = set(INDEX_SITES)

# 説明資料の PDF（ステップ図・フロー図・0工程表・足場計画図など）は docs.json に書く（mitsumori-teian/scripts/publish_docs.py が自動で足す 2026-10-26）
#   {"現場名": [["キー", "表示名"], ...]}。画像は img/ の「キー-番号.svg/jpg」
_dj = ROOT / "docs.json"
for _site, _items in (json.loads(_dj.read_text(encoding="utf-8")) if _dj.exists() else {}).items():
    _s = next((x for x in SITES if x[0] == _site), None)
    if _s is None: SITES.append((_site, [])); _s = SITES[-1]
    _have = {k for k, _ in _s[1]}
    _s[1].extend(tuple(i) for i in _items if i[0] not in _have)

# そのまま置いた HTML（build.py では作らない。ファイルは手で置く）
EXTRA = {}
# 3Dモデルなどは extra.json に書く（mitsumori-teian/scripts/publish_3d.py が自動で足す）。{"現場名": [["ファイル.html", "表示名"], ...]}
_ej = ROOT / "extra.json"
for _site, _items in (json.loads(_ej.read_text(encoding="utf-8")) if _ej.exists() else {}).items():
    EXTRA.setdefault(_site, []).extend(tuple(i) for i in _items)
# 図面の資料がまだ無く、3Dだけある現場も一覧に出す
for _site in EXTRA:
    if _site not in [s_ for s_, _ in SITES]: SITES.append((_site, []))

# 動画（video/ に mp4 を置く。スマホ用に 960×540 へ軽くしたもの）。ページは build.py が作る
VIDEOS = {}
# 動画は videos.json に書く（publish_3d.py --video が自動で足す）。{"現場名": [["ページのキー", "video/….mp4", "表示名"], ...]}
_vj = ROOT / "videos.json"
for _site, _items in (json.loads(_vj.read_text(encoding="utf-8")) if _vj.exists() else {}).items():
    VIDEOS.setdefault(_site, []).extend(tuple(i) for i in _items)
    if _site not in [s_ for s_, _ in SITES]: SITES.append((_site, []))

HEAD = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" type="image/png" href="favicon.png">
<link rel="manifest" href="manifest.json">
<meta name="apple-mobile-web-app-title" content="現場資料">
<meta name="theme-color" content="#e4007f">
<title>{title}</title>
<style>
body{{margin:0;font-family:system-ui,sans-serif;background:#f4f4f4;color:#222}}
header{{background:#e4007f;color:#fff;padding:14px 16px;font-size:18px;font-weight:bold}}
h2{{font-size:17px;margin:20px 16px 8px}}
a.btn{{display:block;margin:8px 16px;padding:16px;background:#fff;border-radius:10px;
  color:#222;text-decoration:none;font-size:17px;box-shadow:0 1px 3px rgba(0,0,0,.15)}}
p.note{{margin:10px 16px;font-size:14px;color:#555}}
img{{display:block;width:100%;height:auto;margin:0 0 12px;background:#fff}}
h2.grp{{margin:22px 12px 6px;padding:8px 12px;background:#e4007f;color:#fff;border-radius:8px;font-size:16px}}
h2.grp.mitsu{{background:#6c757d}}
details.site{{margin:8px 12px;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.15)}}
details.site>summary{{list-style:none;cursor:pointer;padding:16px 44px 16px 16px;font-size:17px;font-weight:bold;position:relative}}
details.site>summary::-webkit-details-marker{{display:none}}
details.site>summary::after{{content:"▼";position:absolute;right:16px;top:50%;transform:translateY(-50%) rotate(-90deg);color:#e4007f;font-size:14px;transition:transform .15s}}
details.site[open]>summary::after{{transform:translateY(-50%)}}
details.site[open]>summary{{border-bottom:1px solid #eee;color:#e4007f}}
details.site a.btn{{margin:8px 10px;background:#fafafa}}
details.site>div{{padding:2px 0 8px}}
div.ret{{margin:10px 16px;padding:12px 14px;background:#fff4d6;border:2px solid #f0b400;
  border-radius:10px;font-size:15px;line-height:1.6}}
</style></head><body>
"""

# Notion への戻り方（Notion アプリの中に開く画面なので、左上の ✕ で閉じる。iPhone で確認 2026-10-23）
RETURN = ('<div class="ret"><b>見終わったら</b><br>'
          '画面の一番左上の <b>✕</b> をタッチすると菊建ページに戻ります</div>')

# 酒井さん専用の一覧の上の部分（検索・4つの段）と、札を替えるボタンの動き（2026-10-31 酒井さん）
#   段: sakusei=📝資料作成中 / shinkou=🏗進行中の工事 / teishutsu=📤見積提出済み / kako=📁過去の資料
#   札は status.json。{"現場名": {"status": "sakusei", "updated": "2026-10-31", "date": "提出日"}}
#   status.json に無い現場は「作成中」に出る（新しく載せた見積の資料）
#   ボタンで替えると GitHub の status.json を直接書き換える（鍵＝このリポジトリだけ書ける Fine-grained token を iPad に1回入れる）
SAKAI_TOP = """<style>
#q{display:block;box-sizing:border-box;width:calc(100% - 24px);margin:10px 12px;padding:12px 14px;font-size:17px;border:2px solid #e4007f;border-radius:10px}
details.grp{margin:14px 0 0}
details.grp>summary{list-style:none;cursor:pointer;margin:8px 12px 6px;padding:10px 14px;background:#e4007f;color:#fff;border-radius:8px;font-size:16px;font-weight:bold}
details.grp>summary::-webkit-details-marker{display:none}
details.grp>summary::before{content:"▶ ";font-size:12px}
details.grp[open]>summary::before{content:"▼ "}
details.grp.shinkou>summary{background:#d35400}
details.grp.teishutsu>summary{background:#2e86c1}
details.grp.kako>summary{background:#6c757d}
details.grp p.empty{margin:4px 16px;color:#888;font-size:14px}
span.day{font-weight:normal;font-size:13px;color:#2e86c1;margin-left:8px}
div.ops{display:flex;flex-wrap:wrap;gap:6px;margin:8px 10px}
div.ops button{flex:1 1 22%;padding:10px 4px;font-size:14px;border:1px solid #ccc;border-radius:8px;background:#fff;color:#333}
div.ops button.on{background:#e4007f;color:#fff;border-color:#e4007f;font-weight:bold}
div.ops button.ask{flex-basis:100%;background:#fff4d6;border-color:#f0b400}
details.cfg{margin:30px 12px;font-size:14px;color:#555}
details.cfg input{width:100%;box-sizing:border-box;padding:10px;font-size:15px;margin:6px 0}
details.cfg button{padding:10px 16px;font-size:15px;margin-right:8px}
#toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:#222;color:#fff;padding:12px 18px;border-radius:10px;font-size:15px;display:none;z-index:9}
</style>
<input id="q" type="search" placeholder="🔍 現場名でさがす（例：福住）">
<details class="grp sakusei" open><summary>📝 資料作成中 <span class="n"></span></summary><div class="box"></div></details>
<details class="grp shinkou" open><summary>🏗 進行中の工事 <span class="n"></span></summary><div class="box"></div></details>
<details class="grp teishutsu"><summary>📤 見積提出済み・返事待ち <span class="n"></span></summary><div class="box"></div></details>
<details class="grp kako"><summary>📁 過去の資料（終わった工事・取れなかった見積） <span class="n"></span></summary><div class="box"></div></details>
<details class="cfg"><summary>⚙ 札を替えるボタンの設定（最初の1回だけ）</summary>
<p>GitHub の鍵（github_pat_ で始まる文字）を貼り付けて「保存」を押してください。鍵はこの iPad の中にだけ残ります。</p>
<input id="tok" type="password" placeholder="github_pat_…" autocomplete="off">
<button id="tokSave">保存</button><button id="tokDel">鍵を消す</button>
<p id="tokState"></p></details>
<div id="toast"></div>
"""
SAKAI_JS = r"""<script>
const API='https://api.github.com/repos/kikukenkogyo/kikuken-genba-shiryo/contents/status.json';
const LABEL={sakusei:'作成中',shinkou:'進行中',teishutsu:'提出済み',kako:'過去'};
let ST=STATUS0;
const tok=()=>localStorage.getItem('ghtok')||'';
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(()=>t.style.display='none',3000);}
function md(d){if(!d)return'';const p=d.split('-');return (+p[1])+'/'+(+p[2]);}
function render(){
  const els=[...document.querySelectorAll('details.site[data-site]')];
  const st=s=>(ST[s]&&ST[s].status)||'sakusei';
  els.sort((a,b)=>{const x=ST[a.dataset.site]||{},y=ST[b.dataset.site]||{};
    return ((y.date||y.updated||'')).localeCompare(x.date||x.updated||'');});
  for(const k in LABEL){document.querySelector('details.grp.'+k+' .box').innerHTML='';}
  for(const el of els){
    const s=el.dataset.site,k=st(s),info=ST[s]||{};
    el.querySelector('span.day').textContent=(k==='teishutsu'&&info.date)?md(info.date)+' 提出':'';
    const ops=el.querySelector('div.ops');ops.innerHTML='';
    for(const kk in LABEL){const b=document.createElement('button');b.textContent=LABEL[kk];if(kk===k)b.className='on';
      b.onclick=()=>{if(kk!==k)save(s,kk);};ops.appendChild(b);}
    const a=document.createElement('button');a.className='ask';a.textContent='📋 Claudeに頼む（現場名をコピー）';
    a.onclick=()=>copy('【'+s+'】の続き：');ops.appendChild(a);
    document.querySelector('details.grp.'+k+' .box').appendChild(el);
  }
  for(const k in LABEL){const g=document.querySelector('details.grp.'+k),n=g.querySelectorAll('details.site').length;
    g.querySelector('span.n').textContent='（'+n+'）';
    if(!n)g.querySelector('.box').innerHTML='<p class="empty">ありません</p>';}
  filter();
}
function filter(){
  const q=document.getElementById('q').value.trim();
  for(const el of document.querySelectorAll('details.site[data-site]'))el.style.display=(!q||el.dataset.site.includes(q))?'':'none';
  if(q)for(const g of document.querySelectorAll('details.grp'))g.open=true;
}
function copy(t){
  const done=()=>toast('コピーしました。Claudeのアプリに貼り付けて、続きを話してください');
  if(navigator.clipboard)navigator.clipboard.writeText(t).then(done,()=>fb());else fb();
  function fb(){const x=document.createElement('textarea');x.value=t;document.body.appendChild(x);x.select();document.execCommand('copy');x.remove();done();}
}
const dec=b=>new TextDecoder().decode(Uint8Array.from(atob(b.replace(/\n/g,'')),c=>c.charCodeAt(0)));
function enc(s){const u=new TextEncoder().encode(s);let r='';for(const c of u)r+=String.fromCharCode(c);return btoa(r);}
function today(){const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
async function save(site,k){
  if(!tok()){alert('最初に、ページの一番下の「⚙ 札を替えるボタンの設定」で鍵を入れてください');return;}
  toast('「'+LABEL[k]+'」に替えています…');
  const H={Authorization:'Bearer '+tok(),Accept:'application/vnd.github+json'};
  for(let i=0;i<3;i++){
    const r=await fetch(API+'?t='+Date.now(),{headers:H,cache:'no-store'});
    if(!r.ok){alert('GitHub に入れませんでした（'+r.status+'）。鍵が正しいか確かめてください');return;}
    const j=await r.json(),obj=JSON.parse(dec(j.content));
    const o=Object.assign({},obj[site]||{});o.status=k;o.updated=today();
    if(k==='teishutsu'&&!o.date)o.date=today();
    obj[site]=o;
    const p=await fetch(API,{method:'PUT',headers:H,body:JSON.stringify({message:'札を替える：'+site+' → '+LABEL[k]+'（iPad）',content:enc(JSON.stringify(obj,null,1)),sha:j.sha})});
    if(p.ok){ST=obj;render();toast('「'+site+'」を「'+LABEL[k]+'」に移しました');return;}
    if(p.status!==409&&p.status!==422){alert('書き換えできませんでした（'+p.status+'）');return;}
  }
  alert('ほかの書き換えとぶつかりました。少し待ってもう一度押してください');
}
async function load(){
  try{
    if(tok()){const r=await fetch(API+'?t='+Date.now(),{headers:{Authorization:'Bearer '+tok()},cache:'no-store'});
      if(r.ok){ST=JSON.parse(dec((await r.json()).content));render();return;}}
    const r=await fetch('status.json?t='+Date.now(),{cache:'no-store'});if(r.ok){ST=await r.json();render();}
  }catch(e){}
}
function tokState(){document.getElementById('tokState').textContent=tok()?'✅ 鍵が入っています（ボタンが使えます）':'まだ鍵が入っていません';}
document.getElementById('tokSave').onclick=()=>{const v=document.getElementById('tok').value.trim();if(v){localStorage.setItem('ghtok',v);document.getElementById('tok').value='';tokState();toast('鍵を保存しました');load();}};
document.getElementById('tokDel').onclick=()=>{localStorage.removeItem('ghtok');tokState();toast('鍵を消しました');};
document.getElementById('q').oninput=filter;
tokState();render();load();
</script>"""

def pages(key):
    # img/ の「キー-番号.svg / .jpg」をページ順に返す（render.py が作る）
    files = [f for f in (ROOT / "img").glob(f"{key}-*.*") if f.suffix in (".svg", ".jpg")]
    return sorted(files, key=lambda f: int(f.stem.rsplit("-", 1)[1]))

def page_count(key):
    return len(pages(key))

out = [HEAD.format(title="各現場の資料"), "<header>各現場の資料（菊建興業）</header>",
       '<p class="note">現場名をタッチすると資料が出ます → 資料をタッチ → 画像を指で広げると拡大できます。</p>', RETURN]
# ホーム画面に追加したとき、この一覧が開くように manifest を外す（iPhone は manifest があると start_url＝入口の一覧を開いてしまう。2026-10-25 確認）
# manifest が無ければ、iPhone は開いているページの URL をそのまま登録する
allout = [HEAD.format(title="全部の資料（見積段階も含む）").replace('<link rel="manifest" href="manifest.json">', "").replace('content="現場資料"', 'content="全部の資料"'), "<header>全部の資料（見積段階も含む）</header>",
          '<p class="note">見積段階の資料も入っています。URL を社外の人に送らないでください。<br>現場名をタッチすると資料が出ます。</p>']
all_uke, all_mitsu = [], []
for site, docs in SITES:
    links = []  # 一覧に出すボタン（INDEX_SITES / INDEX_LINKS にあるものだけ）
    all_links = []  # 酒井さん専用の一覧（全部）
    for key, name in docs:
        n = page_count(key)
        label = name + (f"（{n}枚）" if n > 1 else "")
        b = f'<a class="btn" href="{key}.html">📄 {html.escape(label)}</a>'
        all_links.append(b)
        if site in INDEX_SITES:
            links.append(b)

        pg = [HEAD.format(title=f"{name}｜{site}"), f"<header>{html.escape(name)}</header>",
              f'<p class="note">{html.escape(site)}<br>指で広げると拡大できます。</p>', RETURN]
        for i, f in enumerate(pages(key), 1):
            pg.append(f'<img src="img/{f.name}" alt="{html.escape(name)} {i}ページ" loading="lazy">')
        pg.append(RETURN + '</body></html>')
        (ROOT / f"{key}.html").write_text("\n".join(pg), encoding="utf-8")
    # 画像にしない資料（3Dモデルなど、そのまま置いた HTML）
    for href, label in EXTRA.get(site, []):
        b = f'<a class="btn" href="{href}">{html.escape(label)}</a>'
        all_links.append(b)
        if href in INDEX_LINKS:
            links.append(b)
    for key, src, label in VIDEOS.get(site, []):
        b = f'<a class="btn" href="{key}.html">{html.escape(label)}</a>'
        all_links.append(b)
        if f"{key}.html" in INDEX_LINKS:
            links.append(b)
        pg = [HEAD.format(title=f"{label}｜{site}"), f"<header>{html.escape(label[2:])}</header>",
              f'<p class="note">{html.escape(site)}<br>▶をタッチすると再生します。音が出ます。</p>', RETURN,
              f'<video src="{src}" controls playsinline preload="metadata" style="display:block;width:100%;height:auto;background:#000"></video>',
              RETURN + '</body></html>']
        (ROOT / f"{key}.html").write_text("\n".join(pg), encoding="utf-8")
    # 現場名のトグル（タッチで開くと資料が並ぶ）。現場が増えて一覧が長くなったため（2026-10-29 酒井さん）
    if links:
        out.append(f'<details class="site"><summary>{html.escape(site)}</summary><div>')
        out.extend(links); out.append("</div></details>")
    if all_links:
        # 酒井さん専用の一覧は、status.json の札（作成中／進行中／提出済み／過去）で並べ分ける（2026-10-31 酒井さん）
        # 並べ分けはページを開いたときに JS がやる（iPad のボタンで札を替えたら、すぐ並び替わるように）
        all_mitsu.append(f'<details class="site" data-site="{html.escape(site)}"><summary>{html.escape(site)}<span class="day"></span></summary><div>'
                         '<div class="ops"></div>')
        all_mitsu.extend(all_links); all_mitsu.append("</div></details>")
for _fn, _site in SHARE_PAGES.items():
    _b = []
    for site, docs in SITES:
        if site != _site: continue
        for key, name in docs:
            n = page_count(key)
            _b.append(f'<a class="btn" href="{key}.html">📄 {html.escape(name + (f"（{n}枚）" if n > 1 else ""))}</a>')
        _b += [f'<a class="btn" href="{h}">{html.escape(l)}</a>' for h, l in EXTRA.get(site, [])]
        _b += [f'<a class="btn" href="{k}.html">{html.escape(l)}</a>' for k, _, l in VIDEOS.get(site, [])]
    (ROOT / _fn).write_text("\n".join([HEAD.format(title=_site).replace('<link rel="manifest" href="manifest.json">', ""),
        f"<header>{html.escape(_site)}</header>", '<p class="note">資料をタッチすると開きます。図面は指で広げると拡大できます。3Dモデルは指で回せます。</p>'] + _b + ["</body></html>"]), encoding="utf-8")
out.append("</body></html>")
(ROOT / "index.html").write_text("\n".join(out), encoding="utf-8")
_st = ROOT / "status.json"
STATUS = json.loads(_st.read_text(encoding="utf-8")) if _st.exists() else {}
# python build.py --touch 現場名 … 資料を載せた現場の札を更新（publish_docs.py / publish_3d.py が呼ぶ）
#   札が無い現場 →「作成中」で足す。作成中の現場 → 日付を今日にして一番上へ。提出済み・進行中・過去の札は替えない
import sys, datetime
if "--touch" in sys.argv:
    _site = sys.argv[sys.argv.index("--touch") + 1]
    _o = STATUS.setdefault(_site, {"status": "sakusei"})
    if _o["status"] == "sakusei": _o["updated"] = datetime.date.today().isoformat()
    _st.write_text(json.dumps(STATUS, ensure_ascii=False, indent=1), encoding="utf-8")
allout += [SAKAI_TOP, '<div id="pool" hidden>'] + all_mitsu + ["</div>",
           "<script>const STATUS0=" + json.dumps(STATUS, ensure_ascii=False) + ";</script>", SAKAI_JS]
allout.append("</body></html>")
(ROOT / ALL_INDEX).write_text("\n".join(allout), encoding="utf-8")
print("ok")

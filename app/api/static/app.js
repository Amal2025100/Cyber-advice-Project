const form = document.getElementById('ask-form');
const questionInput = document.getElementById('question');
const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');
const pillEl = document.getElementById('category-pill');
const adviceEl = document.getElementById('advice');

// Auth elements
const signupBtn = document.getElementById('signup-btn');
const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const authStatus = document.getElementById('auth-status');
const historySection = document.getElementById('history');
const historyList = document.getElementById('history-list');
const clearHistoryBtn = document.getElementById('clear-history-btn');

// Session history (client-side only)
const LS_KEY = 'qa_history';
function loadHistory(){
  try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]'); } catch { return []; }
}
function saveHistory(items){ localStorage.setItem(LS_KEY, JSON.stringify(items)); }
function clearHistory(){ localStorage.removeItem(LS_KEY); }
function renderHistory(){
  const items = loadHistory();
  if(historySection) historySection.hidden = false;
  if(!historyList) return;
  historyList.innerHTML = '';
  for(const it of items){
    // Question bubble (right)
    const q = document.createElement('div');
    q.className = 'bubble q';
    q.textContent = it.q;
    historyList.appendChild(q);
    // Answer bubble (left)
    const a = document.createElement('div');
    a.className = 'bubble a';
    a.innerHTML = `<div class="pill" style="margin-bottom:6px;">${categoryLabel(it.category)}</div>${it.advice}`;
    historyList.appendChild(a);
  }
  // scroll to bottom
  historyList.parentElement?.scrollTo({ top: historyList.parentElement.scrollHeight, behavior: 'smooth' });
}
function addEntry(qText, category, advice){
  const items = loadHistory();
  items.push({ q: qText, category, advice, ts: Date.now() });
  saveHistory(items);
  renderHistory();
}

function categoryLabel(cat){
  const map = {
    phishing: 'التصيد',
    passwords: 'كلمات المرور',
    malware: 'برمجيات خبيثة',
    networks: 'أمن الشبكات',
    incident_response: 'الاستجابة للحوادث',
    general: 'عام'
  };
  return map[cat] || cat;
}

// Token helpers
function setToken(t){ localStorage.setItem('token', t); }
function getToken(){ return localStorage.getItem('token') || ''; }
function clearToken(){ localStorage.removeItem('token'); }

function setAuthMessage(msg, isError=false){
  if(!authStatus) return;
  authStatus.hidden = !msg;
  authStatus.textContent = msg || '';
  authStatus.style.color = isError ? '#fca5a5' : '';
}

function updateAuthUI(){
  const hasToken = !!getToken();
  if(signupBtn) signupBtn.style.display = hasToken ? 'none' : '';
  if(loginBtn) loginBtn.style.display = hasToken ? 'none' : '';
  if(logoutBtn) logoutBtn.style.display = hasToken ? '' : 'none';
  if(historySection) historySection.hidden = false; // always show session history
}

// Auth actions
if(signupBtn){
  signupBtn.addEventListener('click', async () => {
    const email = (emailInput?.value || '').trim();
    const password = (passwordInput?.value || '').trim();
    if(!email || !password){ setAuthMessage('يرجى إدخال البريد وكلمة المرور', true); return; }
    setAuthMessage('جاري إنشاء الحساب...');
    try{
      const res = await fetch('/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if(!res.ok){ throw new Error(data?.detail || 'فشل إنشاء الحساب'); }
      setToken(data.access_token);
      setAuthMessage('تم إنشاء الحساب وتسجيل الدخول');
      updateAuthUI();
      renderHistory();
    }catch(err){ setAuthMessage(err.message || 'خطأ غير متوقع', true); }
  });
}

if(loginBtn){
  loginBtn.addEventListener('click', async () => {
    const email = (emailInput?.value || '').trim();
    const password = (passwordInput?.value || '').trim();
    if(!email || !password){ setAuthMessage('يرجى إدخال البريد وكلمة المرور', true); return; }
    setAuthMessage('جاري تسجيل الدخول...');
    try{
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if(!res.ok){ throw new Error(data?.detail || 'بيانات الدخول غير صحيحة'); }
      setToken(data.access_token);
      setAuthMessage('تم تسجيل الدخول');
      updateAuthUI();
      renderHistory();
    }catch(err){ setAuthMessage(err.message || 'خطأ غير متوقع', true); }
  });
}

if(logoutBtn){
  logoutBtn.addEventListener('click', () => {
    clearToken();
    setAuthMessage('تم تسجيل الخروج');
    updateAuthUI();
    historyList.innerHTML = '';
  });
}

// Clear history button
if(clearHistoryBtn){
  clearHistoryBtn.addEventListener('click', () => {
    clearHistory();
    if(historyList) historyList.innerHTML = '';
  });
}

// Ask flow
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = questionInput.value.trim();
  if(!q) return;

  statusEl.hidden = false;
  resultEl.hidden = true;
  statusEl.textContent = 'جاري المعالجة...';

  try {
    const token = getToken();
    // Add a pending bubble for UX
    const pendingId = Date.now();
    const pending = document.createElement('div');
    pending.className = 'bubble a';
    pending.dataset.pending = String(pendingId);
    pending.textContent = '... جاري جلب النصيحة';
    historyList.appendChild(pending);

    const res = await fetch('/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': 'Bearer ' + token } : {})
      },
      body: JSON.stringify({ question: q })
    });
    if(res.status === 401){
      throw new Error('الرجاء تسجيل الدخول أولاً');
    }
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();

    pillEl.textContent = categoryLabel(data.category);
    adviceEl.textContent = data.advice;
    resultEl.hidden = false;
    // Remove pending
    const ph = historyList.querySelector('[data-pending]');
    if(ph) ph.remove();
    // Add to session history
    addEntry(q, data.category, data.advice);
  } catch(err){
    adviceEl.textContent = (err && err.message) ? err.message : 'حدث خطأ غير متوقع. حاول مجدداً.';
    resultEl.hidden = false;
  } finally {
    statusEl.hidden = true;
  }
});

// Init
updateAuthUI();
if(!getToken()){
  // لا يوجد توكن => التوجيه إلى صفحة تسجيل الدخول/إنشاء حساب
  window.location.href = '/auth';
} else {
  renderHistory();
}

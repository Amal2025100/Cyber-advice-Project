// Elements
const signupBtn = document.getElementById('signup-btn');
const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const authStatus = document.getElementById('auth-status');

function setAuthMessage(msg, isError=false){
  if(!authStatus) return;
  authStatus.hidden = !msg;
  authStatus.textContent = msg || '';
}

function setToken(t){ localStorage.setItem('token', t); }
function getToken(){ return localStorage.getItem('token') || ''; }
function clearToken(){ localStorage.removeItem('token'); }

function updateUI(){
  const hasToken = !!getToken();
  if(signupBtn) signupBtn.style.display = hasToken ? 'none' : '';
  if(loginBtn) loginBtn.style.display = hasToken ? 'none' : '';
  if(logoutBtn) logoutBtn.style.display = hasToken ? '' : 'none';
}

function parseErrorDetail(data){
  if(!data) return null;
  if(Array.isArray(data.detail)){
    try{
      return data.detail.map(d => (d.msg || d.type || JSON.stringify(d))).join(' | ');
    }catch{
      return 'Validation error';
    }
  }
  return null;
}

async function withDisabled(btns, fn){
  const arr = Array.isArray(btns) ? btns : [btns];
  arr.forEach(b => b && (b.disabled = true));
  try { return await fn(); } finally { arr.forEach(b => b && (b.disabled = false)); }
}

if(signupBtn){
  signupBtn.addEventListener('click', async () => {
    const email = (emailInput?.value || '').trim();
    const password = (passwordInput?.value || '').trim();
    if(!email || !password){
      setAuthMessage('يرجى إدخال البريد وكلمة المرور', true);
      if(emailInput) emailInput.style.borderColor = email ? '' : '#f87171';
      if(passwordInput) passwordInput.style.borderColor = password ? '' : '#f87171';
      (!email && emailInput ? emailInput : (!password && passwordInput ? passwordInput : null))?.focus();
      return;
    }
    if(emailInput) emailInput.style.borderColor = '';
    if(passwordInput) passwordInput.style.borderColor = '';
    setAuthMessage('جاري إنشاء الحساب...');
    await withDisabled([signupBtn, loginBtn], async () => {
      try{
        const res = await fetch('/auth/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        let data = null;
        try { data = await res.json(); } catch {}
        if(!res.ok){
          const detail = parseErrorDetail(data) || (data && data.detail) || 'فشل إنشاء الحساب';
          throw new Error(detail);
        }
        setToken(data.access_token);
        setAuthMessage('تم إنشاء الحساب وتسجيل الدخول');
        updateUI();
        console.log('Signup success');
        setTimeout(() => { window.location.href = '/'; }, 600);
      }catch(err){
        console.error('Signup error:', err);
        setAuthMessage(err.message || 'خطأ غير متوقع', true);
      }
    });
  });
}

if(loginBtn){
  loginBtn.addEventListener('click', async () => {
    const email = (emailInput?.value || '').trim();
    const password = (passwordInput?.value || '').trim();
    if(!email || !password){ setAuthMessage('يرجى إدخال البريد وكلمة المرور', true); return; }
    setAuthMessage('جاري تسجيل الدخول...');
    await withDisabled([signupBtn, loginBtn], async () => {
      try{
        const res = await fetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        let data = null;
        try { data = await res.json(); } catch {}
        if(!res.ok){
          const detail = parseErrorDetail(data) || (data && data.detail) || 'بيانات الدخول غير صحيحة';
          throw new Error(detail);
        }
        setToken(data.access_token);
        setAuthMessage('تم تسجيل الدخول');
        updateUI();
        console.log('Login success');
        setTimeout(() => { window.location.href = '/'; }, 400);
      }catch(err){
        console.error('Login error:', err);
        setAuthMessage(err.message || 'خطأ غير متوقع', true);
      }
    });
  });
}

if(logoutBtn){
  logoutBtn.addEventListener('click', () => {
    clearToken();
    setAuthMessage('تم تسجيل الخروج');
    updateUI();
  });
}

updateUI();
